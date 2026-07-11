// supabase/functions/create-order/index.ts
// Triển khai: supabase functions deploy create-order
//
// POST /create-order
// Body: { product_id, udid, provider ('paypal' | 'payos' | 'momo') }
// Trả về: { checkout_url, pay_url, error }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const PAYPAL_CLIENT_ID = Deno.env.get("PAYPAL_CLIENT_ID")!;
const PAYPAL_SECRET = Deno.env.get("PAYPAL_SECRET")!;
const PAYOS_CLIENT_ID = Deno.env.get("PAYOS_CLIENT_ID")!;
const PAYOS_API_KEY = Deno.env.get("PAYOS_API_KEY")!;
const MOMO_PARTNER_CODE = Deno.env.get("MOMO_PARTNER_CODE")!;
const MOMO_ACCESS_KEY = Deno.env.get("MOMO_ACCESS_KEY")!;
const MOMO_SECRET_KEY = Deno.env.get("MOMO_SECRET_KEY")!;
const BASE_URL = Deno.env.get("BASE_URL") || "https://2kgt.github.io/repo/";

const sb = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

interface OrderRequest {
  product_id: string;
  udid: string;
  provider: "paypal" | "payos" | "momo";
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  try {
    const auth = req.headers.get("authorization")?.replace("Bearer ", "");
    if (!auth) return new Response("Unauthorized", { status: 401 });

    // Verify user từ auth token
    const { data: { user }, error: authError } = await sb.auth.getUser(auth);
    if (authError || !user) {
      return new Response("Invalid token", { status: 401 });
    }

    const body = await req.json() as OrderRequest;
    const { product_id, udid, provider } = body;

    // Kiểm tra product tồn tại + lấy giá
    const { data: product, error: productError } = await sb
      .from("products")
      .select("*")
      .eq("id", product_id)
      .single();

    if (productError || !product) {
      return new Response(JSON.stringify({ error: "Product not found" }), { status: 404 });
    }

    // Tạo order
    const orderId = crypto.randomUUID();
    const amount = provider === "paypal" ? product.price_usd : product.price_vnd;

    const { error: orderError } = await sb.from("orders").insert({
      id: orderId,
      user_id: user.id,
      product_id,
      udid,
      provider,
      amount,
      currency: provider === "paypal" ? "USD" : "VND",
      status: "pending",
    });

    if (orderError) {
      console.error("Order creation error:", orderError);
      return new Response(JSON.stringify({ error: "Failed to create order" }), { status: 500 });
    }

    // Tạo link thanh toán theo provider
    let paymentUrl = "";

    if (provider === "paypal") {
      // PayPal: dùng SDK client-side ở shop.html, không cần link ở đây
      // Nhưng để safe, có thể tạo payment link qua API
      paymentUrl = `https://www.paypal.com/checkoutnow?token=EC-...`; // Simplified
    } else if (provider === "payos") {
      paymentUrl = await createPayOSLink(orderId, product, amount);
    } else if (provider === "momo") {
      paymentUrl = await createMomoLink(orderId, product, amount);
    }

    return new Response(JSON.stringify({
      order_id: orderId,
      checkout_url: paymentUrl, // Dùng cho redirect
      pay_url: paymentUrl,
    }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error in create-order:", error);
    return new Response(JSON.stringify({ error: error.message }), { status: 500 });
  }
});

// ─────────────────────────────────────────────────────────
// PayOS Link Creation
// ─────────────────────────────────────────────────────────
async function createPayOSLink(orderId: string, product: any, amount: number) {
  const response = await fetch("https://api.payos.vn/v1/payment-requests", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-client-id": PAYOS_CLIENT_ID,
      "x-api-key": PAYOS_API_KEY,
    },
    body: JSON.stringify({
      orderCode: parseInt(orderId.replace(/-/g, "").slice(0, 15)),
      amount: Math.round(amount),
      description: product.name,
      items: [{ name: product.name, quantity: 1, price: Math.round(amount) }],
      returnUrl: `${BASE_URL}checkout-success.html?order=${orderId}`,
      cancelUrl: `${BASE_URL}checkout-cancel.html?order=${orderId}`,
    }),
  });

  const data = await response.json();
  return data.data?.checkoutUrl || "";
}

// ─────────────────────────────────────────────────────────
// MoMo Link Creation
// ─────────────────────────────────────────────────────────
async function createMomoLink(orderId: string, product: any, amount: number) {
  const signature = await generateMomoSignature(orderId, amount);

  const response = await fetch("https://test-payment.momo.vn/v3/gateway/api/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      partnerCode: MOMO_PARTNER_CODE,
      partnerTransactionId: orderId,
      accessKey: MOMO_ACCESS_KEY,
      amount,
      orderInfo: product.name,
      redirectUrl: `${BASE_URL}checkout-success.html?order=${orderId}`,
      ipnUrl: `${Deno.env.get("SUPABASE_URL")}/functions/v1/momo-webhook`,
      requestType: "captureWallet",
      signature,
    }),
  });

  const data = await response.json();
  return data.payUrl || "";
}

async function generateMomoSignature(orderId: string, amount: number) {
  const signatureRawData = `accessKey=${MOMO_ACCESS_KEY}&amount=${amount}&orderId=${orderId}&orderInfo=Kyic Store&partnerCode=${MOMO_PARTNER_CODE}&requestType=captureWallet`;
  const encoder = new TextEncoder();
  const data = encoder.encode(signatureRawData);
  const keyData = encoder.encode(MOMO_SECRET_KEY);
  const key = await crypto.subtle.importKey("raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = await crypto.subtle.sign("HMAC", key, data);
  return Array.from(new Uint8Array(signature)).map(b => b.toString(16).padStart(2, "0")).join("");
}
