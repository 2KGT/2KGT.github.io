// supabase/functions/udid-capture/index.ts
// Triển khai: supabase functions deploy udid-capture --no-verify-jwt
//
// Xử lý 2 loại request:
//   GET  /udid-capture?token=xxx  → trả về .mobileconfig ĐÃ KÝ SỐ để iOS cài
//   POST /udid-capture             → nhận UDID từ Apple sau khi cài profile
//
// ⚠️ PHÁT HIỆN QUAN TRỌNG (đã xác nhận bằng cách tải file tham khảo thật):
// Payload loại "Profile Service" (dùng để lấy UDID) CẦN ĐƯỢC KÝ SỐ
// (CMS/PKCS#7) để iOS thực sự kích hoạt luồng trao đổi DeviceAttributes.
// Bản trước dùng plist XML THUẦN (chưa ký) — dù parse callback đúng,
// Apple có thể ÂM THẦM KHÔNG GỌI callback với profile chưa ký.
// Bản này dùng node-forge để ký .mobileconfig bằng chứng chỉ thật của
// bạn trước khi trả về cho iOS.
//
// ═══════════════════════════════════════════════════════════════════
// CẦN 2 SECRET MỚI (nạp qua `supabase secrets set`, KHÔNG qua GitHub):
//   UDID_SIGN_CERT_PEM_B64  → base64 của file chứng chỉ .pem (public cert)
//   UDID_SIGN_KEY_PEM_B64   → base64 của file private key .pem
// Xem hướng dẫn chuẩn bị ở cuối file này (phần comment).
// ═══════════════════════════════════════════════════════════════════

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import * as asn1js from "https://esm.sh/asn1js@3.0.5";
import * as pkijs from "https://esm.sh/pkijs@3.0.15";
import forge from "https://esm.sh/node-forge@1.3.1";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const FUNCTION_URL = `${SUPABASE_URL.replace(/\/$/, "")}/functions/v1/udid-capture`;

// Chứng chỉ ký profile (bắt buộc để Profile Service hoạt động đúng)
const SIGN_CERT_PEM_B64 = Deno.env.get("UDID_SIGN_CERT_PEM_B64");
const SIGN_KEY_PEM_B64 = Deno.env.get("UDID_SIGN_KEY_PEM_B64");

const sb = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

/**
 * Ký 1 chuỗi plist XML thành CMS/PKCS#7 SignedData (DER binary) bằng
 * chứng chỉ + private key thật của bạn. Đây chính là bước "enroll_signed"
 * mà dịch vụ tham khảo dùng — bắt buộc để Profile Service kích hoạt.
 */
function signMobileconfig(plistXml: string): Uint8Array {
  if (!SIGN_CERT_PEM_B64 || !SIGN_KEY_PEM_B64) {
    throw new Error(
      "Thiếu UDID_SIGN_CERT_PEM_B64 / UDID_SIGN_KEY_PEM_B64 — chưa cấu hình chứng chỉ ký profile"
    );
  }

  const certPem = atob(SIGN_CERT_PEM_B64);
  const keyPem = atob(SIGN_KEY_PEM_B64);

  const cert = forge.pki.certificateFromPem(certPem);
  const privateKey = forge.pki.privateKeyFromPem(keyPem);

  const p7 = forge.pkcs7.createSignedData();
  p7.content = forge.util.createBuffer(plistXml, "utf8");
  p7.addCertificate(cert);
  p7.addSigner({
    key: privateKey,
    certificate: cert,
    digestAlgorithm: forge.pki.oids.sha256,
    authenticatedAttributes: [
      { type: forge.pki.oids.contentType, value: forge.pki.oids.data },
      { type: forge.pki.oids.messageDigest },
      { type: forge.pki.oids.signingTime, value: new Date() },
    ],
  });
  // detached: false → nhúng luôn nội dung plist vào trong CMS
  // (giống hệt cấu trúc file enroll_signed.mobileconfig đã kiểm tra)
  p7.sign({ detached: false });

  const derBinaryString = forge.asn1.toDer(p7.toAsn1()).getBytes();
  const bytes = new Uint8Array(derBinaryString.length);
  for (let i = 0; i < derBinaryString.length; i++) {
    bytes[i] = derBinaryString.charCodeAt(i) & 0xff;
  }
  return bytes;
}

/**
 * Giải mã khối CMS/PKCS#7 SignedData mà Apple POST về, trả lại plist
 * XML gốc nằm bên trong (encapContentInfo). KHÔNG verify chữ ký (chỉ
 * cần đọc nội dung UDID) — đủ dùng cho mục đích lấy device attributes.
 */
async function decodeCmsToPlistText(bodyBytes: Uint8Array): Promise<string> {
  const asn1 = asn1js.fromBER(bodyBytes.buffer);
  if (asn1.offset === -1) {
    throw new Error("Không parse được ASN.1 — dữ liệu không đúng định dạng CMS");
  }
  const contentInfo = new pkijs.ContentInfo({ schema: asn1.result });
  const signedData = new pkijs.SignedData({ schema: contentInfo.content });
  const eContent = signedData.encapContentInfo?.eContent;
  if (!eContent) {
    throw new Error("CMS không chứa encapContentInfo.eContent (không tìm thấy plist bên trong)");
  }
  const plistBytes = eContent.valueBlock.valueHexView as Uint8Array;
  return new TextDecoder("utf-8").decode(plistBytes);
}

/** Đọc giá trị 1 <key>NAME</key><string>...</string> từ plist XML đã giải mã */
function extractPlistString(plistText: string, key: string): string | undefined {
  const re = new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`);
  return plistText.match(re)?.[1]?.trim();
}

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);

  // ─── GET: Trả về .mobileconfig ĐÃ KÝ SỐ ──────────────────────────────
  if (req.method === "GET") {
    const token = url.searchParams.get("token");
    if (!token) {
      return new Response("Missing token", { status: 400 });
    }

    await sb.from("udid_sessions")
      .upsert({ token, udid: null }, { onConflict: "token", ignoreDuplicates: true });

    const plistXml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>PayloadType</key>
      <string>Profile Service</string>
      <key>PayloadVersion</key>
      <integer>1</integer>
      <key>PayloadIdentifier</key>
      <string>com.kyic.udid.${token}</string>
      <key>PayloadUUID</key>
      <string>${token}</string>
      <key>PayloadDisplayName</key>
      <string>Kyic Store — Lấy UDID</string>
      <key>PayloadDescription</key>
      <string>Profile tạm để xác định UDID thiết bị. Tự xoá sau 10 phút.</string>
      <key>URL</key>
      <string>${FUNCTION_URL}?token=${token}</string>
      <key>DeviceAttributes</key>
      <array>
        <string>UDID</string>
        <string>PRODUCT</string>
        <string>VERSION</string>
      </array>
    </dict>
  </array>
  <key>PayloadDisplayName</key>
  <string>Kyic Store — Lấy UDID</string>
  <key>PayloadIdentifier</key>
  <string>com.kyic.udid.request.${token}</string>
  <key>PayloadRemovalDisallowed</key>
  <false/>
  <key>PayloadType</key>
  <string>Configuration</string>
  <key>PayloadUUID</key>
  <string>${token}</string>
  <key>PayloadVersion</key>
  <integer>1</integer>
</dict>
</plist>`;

    try {
      const signedBytes = signMobileconfig(plistXml);
      return new Response(signedBytes, {
        headers: {
          "Content-Type": "application/x-apple-aspen-config",
          "Content-Disposition": `attachment; filename="kyic-udid.mobileconfig"`,
        },
      });
    } catch (e) {
      console.error("Lỗi ký profile:", e);
      return new Response(
        JSON.stringify({ error: "Lỗi ký profile: " + (e as Error).message }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
  }

  // ─── POST: Apple gửi UDID về (dạng CMS/PKCS#7 đã ký) ─────────────────
  if (req.method === "POST") {
    const token = url.searchParams.get("token");
    if (!token) {
      return new Response("Missing token", { status: 400 });
    }

    let udid: string | undefined;
    try {
      const bodyBytes = new Uint8Array(await req.arrayBuffer());
      const plistText = await decodeCmsToPlistText(bodyBytes);
      udid = extractPlistString(plistText, "UDID");
    } catch (e) {
      console.error("Lỗi giải mã CMS:", e);
      try {
        const fallbackText = new TextDecoder().decode(
          new Uint8Array(await req.clone().arrayBuffer())
        );
        udid = extractPlistString(fallbackText, "UDID");
      } catch { /* bỏ qua, udid vẫn undefined */ }
    }

    if (!udid) {
      return new Response(
        JSON.stringify({ error: "Không đọc được UDID từ payload CMS" }),
        { status: 422, headers: { "Content-Type": "application/json" } }
      );
    }

    const { error } = await sb.from("udid_sessions")
      .update({ udid })
      .eq("token", token);

    if (error) {
      console.error("Supabase update error:", error);
      return new Response("DB error", { status: 500 });
    }

    // Cấu hình kết thúc (xác nhận) — KHÔNG bắt buộc phải ký lại vì đây
    // chỉ là màn hình "Done" hiển thị cho user, không ảnh hưởng đến
    // việc đã lấy được UDID hay chưa (đã lưu vào DB ở trên).
    const successPlist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array/>
  <key>PayloadDisplayName</key>
  <string>✅ Kyic Store — UDID đã được ghi nhận</string>
  <key>PayloadIdentifier</key>
  <string>com.kyic.udid.done.${token}</string>
  <key>PayloadRemovalDisallowed</key>
  <false/>
  <key>PayloadType</key>
  <string>Configuration</string>
  <key>PayloadUUID</key>
  <string>${token}</string>
  <key>PayloadVersion</key>
  <integer>1</integer>
</dict>
</plist>`;

    return new Response(successPlist, {
      headers: { "Content-Type": "application/x-apple-aspen-config" },
    });
  }

  return new Response("Method not allowed", { status: 405 });
});

// ═══════════════════════════════════════════════════════════════════
// HƯỚNG DẪN CHUẨN BỊ 2 SECRET (chạy trên máy bạn, KHÔNG dán key vào chat)
// ═══════════════════════════════════════════════════════════════════
//
// Nếu bạn có sẵn cert dạng .p12/.pfx (phổ biến với Apple Developer):
//
//   openssl pkcs12 -in yourcert.p12 -clcerts -nokeys -out cert.pem
//   openssl pkcs12 -in yourcert.p12 -nocerts -nodes -out key.pem
//
// Nếu bạn đã có sẵn cert.pem + key.pem thì bỏ qua bước trên.
//
// Sau đó base64 hoá cả 2 file:
//
//   base64 -i cert.pem -o cert_b64.txt
//   base64 -i key.pem  -o key_b64.txt
//
// Nạp vào Supabase (KHÔNG commit lên GitHub, chỉ chạy lệnh CLI):
//
//   supabase secrets set UDID_SIGN_CERT_PEM_B64="$(cat cert_b64.txt)"
//   supabase secrets set UDID_SIGN_KEY_PEM_B64="$(cat key_b64.txt)"
//
// Rồi deploy lại:
//
//   supabase functions deploy udid-capture --no-verify-jwt
//
// Sau khi xong, XOÁ các file cert.pem/key.pem/*_b64.txt khỏi máy tính
// (không cần giữ lại, và tuyệt đối không để lộ ra ngoài).
// ═══════════════════════════════════════════════════════════════════
