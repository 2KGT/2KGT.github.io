// supabase/functions/udid-capture/index.ts
// Triển khai: supabase functions deploy udid-capture --no-verify-jwt
//
// Xử lý 2 loại request:
//   GET  /udid-capture?token=xxx  → trả về .mobileconfig để iOS cài
//   POST /udid-capture             → nhận UDID từ Apple sau khi cài profile
//
// ⚠️ FIX QUAN TRỌNG: Khi cài profile loại "Profile Service", Apple KHÔNG
// POST về XML thuần — mà gửi 1 khối NHỊ PHÂN đã ký số dạng CMS/PKCS#7
// (giống file .p7s) BỌC bên trong 1 plist. Bản cũ dùng regex trên
// req.text() nên KHÔNG BAO GIỜ khớp được (dữ liệu là binary đã ký,
// không phải XML thuần) → UDID không bao giờ lưu được.
// Bản này dùng pkijs/asn1js để giải mã đúng CMS SignedData, lấy plist
// gốc bên trong ra, rồi mới regex trên plist ĐÃ GIẢI MÃ.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import * as asn1js from "https://esm.sh/asn1js@3.0.5";
import * as pkijs from "https://esm.sh/pkijs@3.0.15";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
// URL Edge Function đúng của Supabase: <project>.supabase.co/functions/v1/<tên>
const FUNCTION_URL = `${SUPABASE_URL.replace(/\/$/, "")}/functions/v1/udid-capture`;

const sb = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

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

  // ─── GET: Trả về .mobileconfig ──────────────────────────────────────
  if (req.method === "GET") {
    const token = url.searchParams.get("token");
    if (!token) {
      return new Response("Missing token", { status: 400 });
    }

    // Tạo session nếu chưa có (idempotent)
    await sb.from("udid_sessions")
      .upsert({ token, udid: null }, { onConflict: "token", ignoreDuplicates: true });

    // .mobileconfig payload — Apple sẽ POST UDID về URL này (dạng CMS đã ký)
    const mobileconfig = `<?xml version="1.0" encoding="UTF-8"?>
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
        <string>IMEI</string>
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

    return new Response(mobileconfig, {
      headers: {
        "Content-Type": "application/x-apple-aspen-config",
        "Content-Disposition": `attachment; filename="kyic-udid.mobileconfig"`,
      },
    });
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
      // Fallback: một số thiết bị/tình huống hiếm gặp Apple gửi plist
      // thuần không bọc CMS — thử regex trực tiếp trước khi bỏ cuộc.
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

    // Lưu UDID vào Supabase (Service Role Key bỏ qua RLS)
    const { error } = await sb.from("udid_sessions")
      .update({ udid })
      .eq("token", token);

    if (error) {
      console.error("Supabase update error:", error);
      return new Response("DB error", { status: 500 });
    }

    // Trả về thông báo thành công cho iOS
    // (iOS sẽ hiển thị màn hình xác nhận "Profile đã được ghi nhận")
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

