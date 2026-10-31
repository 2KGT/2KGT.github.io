// supabase/functions/issue-license/index.ts
// Triển khai: supabase functions deploy issue-license
//
// POST /issue-license
// Body: { product_id, udid, provider, txn_id }
// Trả về: { license_key, expires_at, error }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const PAYPAL_CLIENT_ID = Deno.env.get("PAYPAL_CLIENT_ID")!;
const PAYPAL_SECRET = Deno.env.get("PAYPAL_SECRET")!;
const LICENSE_PRIVATE_KEY = Deno.env.get("LICENSE_PRIVATE_KEY")!;

const sb = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

interface LicenseRequest {
  product_id: string;
  udid: string;
  provider: "paypal" | "payos" | "momo";
  txn_id: string;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  try {
    const auth = req.headers.get("authorization")?.replace("Bearer ", "");
    if (!auth) return new Response("Unauthorized", { status: 401 });

    const { data: { user }, error: authError } = await sb.auth.getUser(auth);
    if (authError || !user) {
      return new Response("Invalid token", { status: 401 });
    }

    const body = await req.json() as LicenseRequest;
    const { product_id, udid, provider, txn_id } = body;

    // Kiểm tra order tồn tại + đã thanh toán
    const { data: order, error: orderError } = await sb
      .from("orders")
      .select("*")
      .eq("user_id", user.id)
      .eq("product_id", product_id)
      .eq("provider_txn_id", txn_id)
      .single();

    if (orderError || !order) {
      return new Response(JSON.stringify({ error: "Order not found" }), { status: 404 });
    }

    // Verify thanh toán thành công (tuỳ provider)
    const paymentVerified = await verifyPayment(provider, txn_id, order.amount);
    if (!paymentVerified) {
      return new Response(JSON.stringify({ error: "Payment not verified" }), { status: 402 });
    }

    // Cập nhật order status → paid
    await sb.from("orders")
      .update({ status: "paid", paid_at: new Date().toISOString() })
      .eq("id", order.id);

    // Tạo license key (ký số)
    const expiresAt = new Date();
    expiresAt.setFullYear(expiresAt.getFullYear() + 1); // 1 năm

    const licenseKey = await signLicense(udid, product_id, expiresAt);

    // Insert license vào DB
    const { error: licenseError } = await sb.from("licenses").insert({
      order_id: order.id,
      user_id: user.id,
      product_id,
      udid,
      license_key: licenseKey,
      expires_at: expiresAt.toISOString(),
    });

    if (licenseError) {
      console.error("License insert error:", licenseError);
      return new Response(JSON.stringify({ error: "Failed to create license" }), { status: 500 });
    }

    return new Response(JSON.stringify({
      license_key: licenseKey,
      expires_at: expiresAt.toISOString(),
      product_id,
      udid,
    }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error in issue-license:", error);
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
});

// ─────────────────────────────────────────────────────────
// PAYMENT VERIFICATION
// ─────────────────────────────────────────────────────────
async function verifyPayment(provider: string, txnId: string, amount: number): Promise<boolean> {
  if (provider === "paypal") {
    return await verifyPayPal(txnId);
  } else if (provider === "payos") {
    return await verifyPayOS(txnId, amount);
  } else if (provider === "momo") {
    return await verifyMoMo(txnId, amount);
  }
  return false;
}

async function verifyPayPal(txnId: string): Promise<boolean> {
  // Get PayPal access token
  const auth = btoa(`${PAYPAL_CLIENT_ID}:${PAYPAL_SECRET}`);
  const tokenResp = await fetch("https://api-m.paypal.com/v1/oauth2/token", {
    method: "POST",
    headers: {
      "Authorization": `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",
  });

  const tokenData = await tokenResp.json();
  const accessToken = tokenData.access_token;

  // Verify transaction
  const verifyResp = await fetch(`https://api-m.paypal.com/v2/checkout/orders/${txnId}`, {
    headers: {
      "Authorization": `Bearer ${accessToken}`,
    },
  });

  const order = await verifyResp.json();
  return order.status === "COMPLETED";
}

async function verifyPayOS(txnId: string, amount: number): Promise<boolean> {
  // PayOS: dùng API để check transaction status
  // Simplified — production cần verify signature
  return true; // TODO: implement PayOS verification
}

async function verifyMoMo(txnId: string, amount: number): Promise<boolean> {
  // MoMo: dùng IPN callback (webhook), hoặc query API
  // Simplified — production cần verify signature
  return true; // TODO: implement MoMo verification
}

// ─────────────────────────────────────────────────────────
// LICENSE SIGNING (Ed25519)
// ─────────────────────────────────────────────────────────
async function signLicense(udid: string, productId: string, expiresAt: Date): Promise<string> {
  const payload = {
    udid,
    pkg: productId,
    exp: Math.floor(expiresAt.getTime() / 1000),
  };

  const payloadBytes = new TextEncoder().encode(JSON.stringify(payload, null, 0));

  // Import private key (should be stored securely, not in code)
  const keyData = Deno.env.get("LICENSE_PRIVATE_KEY_B64");
  if (!keyData) throw new Error("Missing LICENSE_PRIVATE_KEY_B64");

  const binaryKey = Uint8Array.from(atob(keyData), c => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("raw", binaryKey, { name: "Ed25519" }, false, ["sign"]);

  // Sign payload
  const signature = await crypto.subtle.sign("Ed25519", key, payloadBytes);

  // Return base64(payload).base64(signature)
  const payloadB64 = btoa(String.fromCharCode(...new Uint8Array(payloadBytes)));
  const signatureB64 = btoa(String.fromCharCode(...new Uint8Array(signature)));

  return `${payloadB64}.${signatureB64}`;
}
