// Configuration
const API_BASE_URL = "https://mpesabeginner.vercel.app/api/v1/b2c";
const WS_URL = "wss://mpesabeginner.vercel.app/ws/payments";

// Store current payment request
let currentPayment = {
    conversation_id: null,
    originator_conversation_id: null,
};

// WebSocket connection
let ws = null;
let reconnectInterval = null;

// DOM Elements
const form = document.getElementById("b2cForm");
const phoneInput = document.getElementById("phoneNumber");
const amountInput = document.getElementById("amount");
const commandSelect = document.getElementById("commandId");
const remarksInput = document.getElementById("remarks");
const occasionInput = document.getElementById("occasion");
const submitBtn = document.getElementById("submitBtn");
const responseBox = document.getElementById("responseBox");
const wsStatus = document.getElementById("wsStatus");
const commandInfo = document.getElementById("commandInfo");

// Command ID descriptions
const commandDescriptions = {
    BusinessPayment: "Standard business payment for registered M-Pesa customers",
    SalaryPayment: "Salary payment - supports both registered and unregistered M-Pesa users",
    PromotionPayment: "Promotional payment with congratulatory message (registered only)"
};

// ==================== WebSocket Functions ====================

function connectWebSocket() {
    try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log("✅ WebSocket connected");
            updateWSStatus(true);
            clearInterval(reconnectInterval);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log("📨 WebSocket message received:", data);

                // Check if this is a B2C result
                if (data.type === "b2c_result") {
                    handleB2CCallback(data.data);
                } else if (data.type === "b2c_timeout") {
                    handleB2CTimeout(data.data);
                } else {
                    // Check if it matches our current payment
                    if (
                        data.conversation_id === currentPayment.conversation_id ||
                        data.originator_conversation_id === currentPayment.originator_conversation_id
                    ) {
                        handleB2CCallback(data);
                    }
                }
            } catch (error) {
                console.error("Error parsing WebSocket message:", error);
            }
        };

        ws.onerror = (error) => {
            console.error("❌ WebSocket error:", error);
            updateWSStatus(false);
        };

        ws.onclose = () => {
            console.log("🔴 WebSocket disconnected");
            updateWSStatus(false);
            // Attempt to reconnect after 3 seconds
            reconnectInterval = setInterval(() => {
                console.log("🔄 Attempting to reconnect...");
                connectWebSocket();
            }, 3000);
        };
    } catch (error) {
        console.error("Failed to connect WebSocket:", error);
        updateWSStatus(false);
    }
}

function updateWSStatus(connected) {
    if (connected) {
        wsStatus.textContent = "🟢 Connected";
        wsStatus.className = "ws-status ws-connected";
    } else {
        wsStatus.textContent = "🔴 Disconnected";
        wsStatus.className = "ws-status ws-disconnected";
    }
}

// ==================== Utility Functions ====================

function generateTimestamp() {
    return new Date().toISOString();
}

function generateUniqueId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function formatPhoneNumber(phone) {
    // Remove spaces, dashes, and plus sign
    phone = phone.replace(/[\s\-+]/g, "");
    
    // Convert 07XX to 2547XX
    if (phone.startsWith("0")) {
        phone = "254" + phone.substring(1);
    }
    
    return phone;
}

function appendToResponseBox(message, status = null) {
    const timestamp = new Date().toLocaleTimeString();
    
    if (status) {
        const badge = document.createElement("span");
        badge.className = `status-badge status-${status}`;
        badge.textContent = status.toUpperCase();
        responseBox.innerHTML = "";
        responseBox.appendChild(badge);
        responseBox.appendChild(document.createTextNode("\n"));
    }
    
    responseBox.textContent += `[${timestamp}] ${message}\n`;
    responseBox.scrollTop = responseBox.scrollHeight;
}

function clearResponseBox() {
    responseBox.innerHTML = '<span style="color: #999;">Processing payment...</span>';
}

// ==================== B2C Payment Functions ====================

async function initiateB2CPayment(payload) {
    const timestamp = generateTimestamp();
    
    try {
        const response = await fetch(`${API_BASE_URL}/payment`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Request-Timestamp": timestamp,
                "X-Merchant-Key": "merchant_123", // Replace with your actual key
            },
            body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail?.error_message || 
                JSON.stringify(data.detail) || 
                "Payment request failed"
            );
        }

        return data;
    } catch (error) {
        throw error;
    }
}

function handleB2CCallback(callbackData) {
    console.log("Processing B2C callback:", callbackData);
    
    // Clear previous content
    responseBox.innerHTML = "";
    
    if (callbackData.result_code === 0) {
        // Successful payment
        appendToResponseBox("✅ Payment Successful!", "success");
        appendToResponseBox(`Transaction ID: ${callbackData.transaction_id}`);
        
        // Extract and display transaction details
        if (callbackData.result_parameters) {
            const items = callbackData.result_parameters.ResultParameter || [];
            const details = {};
            items.forEach(item => {
                details[item.Key] = item.Value;
            });
            
            appendToResponseBox("\n📊 Transaction Details:");
            appendToResponseBox(`Amount: KES ${details.TransactionAmount}`);
            appendToResponseBox(`Receipt: ${details.TransactionReceipt}`);
            appendToResponseBox(`Recipient: ${details.ReceiverPartyPublicName}`);
            appendToResponseBox(`Completed: ${details.TransactionCompletedDateTime}`);
            
            if (details.B2CRecipientIsRegisteredCustomer) {
                const isRegistered = details.B2CRecipientIsRegisteredCustomer === "Y";
                appendToResponseBox(
                    `Customer Status: ${isRegistered ? "Registered" : "Unregistered"}`
                );
            }
            
            appendToResponseBox("\n💰 Account Balances:");
            appendToResponseBox(
                `Working Account: KES ${details.B2CWorkingAccountAvailableFunds}`
            );
            appendToResponseBox(
                `Utility Account: KES ${details.B2CUtilityAccountAvailableFunds}`
            );
        }
    } else {
        // Failed payment
        appendToResponseBox("❌ Payment Failed!", "error");
        appendToResponseBox(`Error Code: ${callbackData.result_code}`);
        appendToResponseBox(`Description: ${callbackData.result_desc}`);
        
        // Handle common error codes
        if (callbackData.result_code === 2001) {
            appendToResponseBox("\n⚠️ Initiator information is invalid");
            appendToResponseBox("Check your INITIATOR_NAME and SECURITY_CREDENTIAL");
        } else if (callbackData.result_code === 1) {
            appendToResponseBox("\n⚠️ Insufficient balance in account");
        }
    }
    
    // Re-enable submit button
    submitBtn.disabled = false;
    submitBtn.textContent = "Send Payment";
    submitBtn.classList.remove("loading");
}

function handleB2CTimeout(timeoutData) {
    console.log("B2C payment timeout:", timeoutData);
    
    responseBox.innerHTML = "";
    appendToResponseBox("⏱️ Payment Request Timeout", "error");
    appendToResponseBox("The payment request took too long to process.");
    appendToResponseBox("Please try again or contact support.");
    
    // Re-enable submit button
    submitBtn.disabled = false;
    submitBtn.textContent = "Send Payment";
    submitBtn.classList.remove("loading");
}

// ==================== Event Listeners ====================

// Update command info when selection changes
commandSelect.addEventListener("change", (e) => {
    commandInfo.textContent = commandDescriptions[e.target.value];
});

// Form submission
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.textContent = "Processing...";
    submitBtn.classList.add("loading");
    
    // Clear response box
    clearResponseBox();
    
    // Prepare payload
    const payload = {
        phone_number: formatPhoneNumber(phoneInput.value.trim()),
        amount: parseInt(amountInput.value),
        command_id: commandSelect.value,
        remarks: remarksInput.value.trim() || "Payment",
        occasion: occasionInput.value.trim() || null,
        originator_conversation_id: generateUniqueId(),
    };
    
    appendToResponseBox("📤 Initiating B2C payment...", "processing");
    appendToResponseBox(`Phone: ${payload.phone_number}`);
    appendToResponseBox(`Amount: KES ${payload.amount}`);
    appendToResponseBox(`Type: ${payload.command_id}`);
    
    try {
        const response = await initiateB2CPayment(payload);
        
        // Store payment identifiers
        currentPayment.conversation_id = response.conversation_id;
        currentPayment.originator_conversation_id = response.originator_conversation_id;
        
        // Display initial response
        responseBox.innerHTML = "";
        appendToResponseBox("✅ Payment Request Accepted", "pending");
        appendToResponseBox(`Conversation ID: ${response.conversation_id}`);
        appendToResponseBox(`Status: ${response.response_description}`);
        appendToResponseBox("\n⏳ Waiting for payment confirmation...");
        appendToResponseBox("This may take a few moments.");
        
        // Note: The actual result will come via WebSocket callback
        // Button will be re-enabled when callback is received
        
    } catch (error) {
        responseBox.innerHTML = "";
        appendToResponseBox("❌ Payment Request Failed", "error");
        appendToResponseBox(`Error: ${error.message}`);
        
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = "Send Payment";
        submitBtn.classList.remove("loading");
    }
});

// Phone number formatting on input
phoneInput.addEventListener("blur", (e) => {
    try {
        const formatted = formatPhoneNumber(e.target.value);
        e.target.value = formatted;
    } catch (error) {
        // Invalid format, let validation handle it
    }
});

// ==================== Initialize ====================

document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 B2C Payment Interface Loaded");
    console.log(`API: ${API_BASE_URL}`);
    console.log(`WebSocket: ${WS_URL}`);
    
    // Connect WebSocket
    connectWebSocket();
    
    // Set default command info
    commandInfo.textContent = commandDescriptions[commandSelect.value];
});

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
    if (ws) {
        ws.close();
    }
    if (reconnectInterval) {
        clearInterval(reconnectInterval);
    }
});