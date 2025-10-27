const API_BASE_URL = "https://mpesabeginner.vercel.app/api/v1/stk-push"; // change to your deployed domain when live
const WS_URL = "wss://mpesabeginner.vercel.app/ws/payments";

let currentRequest = {
  merchant_request_id: null,
  checkout_request_id: null,
};


function generateTimestamp() {
  return new Date().toISOString();
}


// --- Setup form ---
document.addEventListener("DOMContentLoaded", () => {
  const form = document.createElement("form");
  form.innerHTML = `
    <h2>Initiate STK Push</h2>
    <label>Phone Number:</label>
    <input type="text" id="phone_number" placeholder="2547XXXXXXXX" required><br><br>
    
    <label>Amount:</label>
    <input type="number" id="amount" min="1" placeholder="Amount" required><br><br>
    
    <label>Account Reference:</label>
    <input type="text" id="account_reference" maxlength="12" placeholder="INV001" required><br><br>
    
    <label>Transaction Description:</label>
    <input type="text" id="transaction_desc" maxlength="13" placeholder="Payment" required><br><br>
    
    <button type="submit">Pay Now</button>
  `;

  const responseBox = document.createElement("pre");
  responseBox.id = "response";
  responseBox.style.border = "1px solid #ccc";
  responseBox.style.padding = "10px";
  responseBox.style.marginTop = "20px";
  responseBox.style.background = "#f9f9f9";

  document.body.appendChild(form);
  document.body.appendChild(responseBox);

  // --- WebSocket connection ---
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => console.log("✅ Connected to payment WebSocket");
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // 🧠 Only show messages that match this session’s STK push
    if (
      data.merchant_request_id === currentRequest.merchant_request_id &&
      data.checkout_request_id === currentRequest.checkout_request_id
    ) {
      document.getElementById("response").textContent +=
        `\n💰 Payment Update: ${JSON.stringify(data, null, 2)}\n`;
    } else {
      console.log("Ignoring unrelated callback:", data);
    }
  };
  ws.onerror = (err) => console.error("❌ WebSocket error:", err);

  // --- Form submit handler ---
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      phone_number: document.getElementById("phone_number").value.trim(),
      amount: parseInt(document.getElementById("amount").value),
      account_reference: document.getElementById("account_reference").value.trim(),
      transaction_desc: document.getElementById("transaction_desc").value.trim(),
    };

    const timestamp = generateTimestamp();
    responseBox.textContent = "Processing payment...\n";

    try {
      const res = await fetch(`${API_BASE_URL}/initiate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Request-Timestamp": timestamp,
          "X-Merchant-key": "merchant_123", // replace with your actual key
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        responseBox.textContent = `❌ Error: ${JSON.stringify(data.detail || data, null, 2)}`;
        return;
      }

      // ✅ Store IDs for this session
      currentRequest.merchant_request_id = data.merchant_request_id;
      currentRequest.checkout_request_id = data.checkout_request_id;

      responseBox.textContent = `✅ STK Push Sent!\n${JSON.stringify(data, null, 2)}`;
    } catch (error) {
      responseBox.textContent = `⚠️ Request Failed: ${error.message}`;
    }
  });
});
