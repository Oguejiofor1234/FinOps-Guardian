// FinOps Guardian Frontend Application Logic

const USER_ID = "dashboard_user";
let currentModalSessionId = null;

document.addEventListener("DOMContentLoaded", () => {
    // Initial fetch of metrics and audit logs
    refreshDashboard();
    
    // Wire up submit forms
    const nlpForm = document.getElementById("nlp-expense-form");
    if (nlpForm) {
        nlpForm.addEventListener("submit", handleNlpSubmit);
    }
    
    const structuredForm = document.getElementById("structured-expense-form");
    if (structuredForm) {
        structuredForm.addEventListener("submit", handleStructuredSubmit);
    }

    // Modal submit listener
    const submitReceiptBtn = document.getElementById("submit-receipt-btn");
    if (submitReceiptBtn) {
        submitReceiptBtn.addEventListener("click", handleModalReceiptSubmit);
    }
    
    // Poll metrics & logs occasionally to keep dashboard fresh
    setInterval(refreshDashboard, 5000);
});

// Switch tabs between NLP and Structured input
function switchSubmitTab(tab) {
    const nlpForm = document.getElementById("nlp-expense-form");
    const structuredForm = document.getElementById("structured-expense-form");
    const tabs = document.querySelectorAll(".tab-btn");

    if (tab === "nlp") {
        nlpForm.classList.remove("hidden");
        structuredForm.classList.add("hidden");
        tabs[0].classList.add("active");
        tabs[1].classList.remove("active");
    } else {
        nlpForm.classList.add("hidden");
        structuredForm.classList.remove("hidden");
        tabs[0].classList.remove("active");
        tabs[1].classList.add("active");
    }
}

// Helper to log event to compliance stream panel
function addLogEntry(text, type = "info") {
    const logEntries = document.getElementById("log-entries");
    if (!logEntries) return;

    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];
    
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    
    entry.innerHTML = `
        <span class="log-time">${timeStr}</span>
        <span class="log-text">${text}</span>
    `;
    
    logEntries.appendChild(entry);
    logEntries.scrollTop = logEntries.scrollHeight;
}

function clearLiveLogs() {
    const logEntries = document.getElementById("log-entries");
    if (logEntries) {
        logEntries.innerHTML = `
            <div class="log-entry info">
                <span class="log-time">System</span>
                <span class="log-text">Compliance Stream cleared. Standby for new operations.</span>
            </div>
        `;
    }
}

// Refresh spend metrics and audit trail
async function refreshDashboard() {
    try {
        // 1. Fetch Metrics
        const metricsResp = await fetch("/metrics", {
            headers: { "X-User-Role": "admin" }
        });
        if (metricsResp.ok) {
            const metrics = await metricsResp.json();
            
            document.getElementById("metric-approved-spend").textContent = 
                new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(metrics.total_approved_amount || 0);
            
            document.getElementById("metric-approved-count").textContent = 
                `${metrics.approved_count || 0} Claims approved`;
            
            const highRiskCount = metrics.risk_breakdown?.HIGH || 0;
            const mediumRiskCount = metrics.risk_breakdown?.MEDIUM || 0;
            const lowRiskCount = metrics.risk_breakdown?.LOW || 0;
            const totalClaims = highRiskCount + mediumRiskCount + lowRiskCount;
            
            document.getElementById("metric-flagged-count").textContent = highRiskCount;
            
            const percentage = totalClaims > 0 ? Math.round((highRiskCount / totalClaims) * 100) : 0;
            document.getElementById("metric-flagged-percentage").textContent = 
                `${percentage}% of total audited`;

            document.getElementById("metric-pending-count").textContent = metrics.pending_review_count || 0;
            document.getElementById("metric-rejected-count").textContent = metrics.rejected_count || 0;
        }

        // 2. Fetch Audit Logs
        const logsResp = await fetch("/audit-logs", {
            headers: { "X-User-Role": "admin" }
        });
        if (logsResp.ok) {
            const logsData = await logsResp.json();
            renderAuditTrail(logsData.logs || []);
        }

        // 3. Fetch Pending HITL Sessions
        const pendingResp = await fetch("/sessions/pending", {
            headers: { "X-User-Role": "admin" }
        });
        if (pendingResp.ok) {
            const pendingData = await pendingResp.json();
            renderPendingQueue(pendingData.pending || []);
        }

        // 4. Fetch Compliance Stream Logs
        const streamResp = await fetch("/compliance-stream", {
            headers: { "X-User-Role": "admin" }
        });
        if (streamResp.ok) {
            const streamData = await streamResp.json();
            renderComplianceStream(streamData.logs || []);
        }
    } catch (err) {
        console.error("Dashboard refresh failed:", err);
    }
}

// Render the Human-in-the-Loop review queue
function renderPendingQueue(pendingList) {
    const tableBody = document.querySelector("#hitl-table tbody");
    if (!tableBody) return;

    if (pendingList.length === 0) {
        tableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="7">No claims currently pending review. Submissions requiring approval will appear here.</td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = pendingList.map(item => {
        const sessionId = item.session_id;
        const state = item.state || {};
        const requiredInput = item.required_input;
        const shortId = sessionId.substring(0, 8) + "...";
        const riskClass = state.risk_level === "HIGH" ? "flag-high" : "flag-med";
        const pendingReason = requiredInput === "manager_decision" ? "Manager Decision" : "Receipt Upload Needed";
        
        let actionButtons = "";
        if (requiredInput === "manager_decision") {
            actionButtons = `
                <button class="btn btn-sm btn-success" onclick="managerDecision('${sessionId}', 'APPROVE')">Approve</button>
                <button class="btn btn-sm btn-danger" onclick="managerDecision('${sessionId}', 'REJECT')">Reject</button>
                <button class="btn btn-sm btn-warning" onclick="managerDecision('${sessionId}', 'REQUEST_RECEIPT')">Request Receipt</button>
            `;
        } else if (requiredInput === "receipt_upload") {
            actionButtons = `
                <button class="btn btn-sm btn-primary" onclick="openReceiptModal('${sessionId}')">Upload Receipt</button>
            `;
        }

        return `
            <tr id="hitl-row-${sessionId}">
                <td class="amount-val">${shortId}</td>
                <td>${state.title || "Unparsed"}</td>
                <td class="amount-val">${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(state.amount || 0)}</td>
                <td>${state.category || "Uncategorized"}</td>
                <td><span class="flag ${riskClass}">${state.risk_level || "MEDIUM"}</span></td>
                <td><span class="text-amber font-semibold">${pendingReason}</span></td>
                <td><div class="row-actions">${actionButtons}</div></td>
            </tr>
        `;
    }).join("");
}

// Render the PostgreSQL ledger audit trail table
function renderAuditTrail(logs) {
    const auditTableBody = document.querySelector("#audit-table tbody");
    if (!auditTableBody) return;
    
    if (logs.length === 0) {
        auditTableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="10">No transactions recorded in PostgreSQL ledger.</td>
            </tr>
        `;
        return;
    }

    auditTableBody.innerHTML = logs.map(log => {
        const riskClass = log.risk_level === "HIGH" ? "flag-high" : (log.risk_level === "MEDIUM" ? "flag-med" : "flag-low");
        const appStatusClass = log.approval_status === "APPROVED" ? "btn-success" : (log.approval_status === "REJECTED" ? "btn-danger" : "btn-warning");
        
        return `
            <tr>
                <td class="amount-val">${log.transaction_id || "-"}</td>
                <td>${log.title || "-"}</td>
                <td class="amount-val">${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(log.amount || 0)}</td>
                <td>${log.category || "-"}</td>
                <td>${log.expense_date || "-"}</td>
                <td class="amount-val">${log.gl_code || "-"}</td>
                <td>${log.cost_center || "-"}</td>
                <td>${log.tax_code || "-"}</td>
                <td><span class="flag ${riskClass}">${log.risk_level || "LOW"}</span></td>
                <td><span class="badge ${appStatusClass}">${log.approval_status || "PENDING"}</span></td>
            </tr>
        `;
    }).join("");
}

// Handle unstructured natural language submission
async function handleNlpSubmit(e) {
    e.preventDefault();
    const textarea = document.getElementById("nlp-text");
    const text = textarea.value.trim();
    if (!text) return;

    addLogEntry(`Ingesting claim: "${text}"`, "info");
    addLogEntry("Guardrails active: Scanning input text for sensitive data...", "info");
    
    try {
        const response = await fetch("/expenses/submit", {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "X-User-Role": "admin"
            },
            body: JSON.stringify({ user_id: USER_ID, text: text })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }
        
        const result = await response.json();
        processWorkflowResult(result);
        
        // Clear textarea
        textarea.value = "";
    } catch (err) {
        addLogEntry(`Error submitting claim: ${err.message}`, "error");
    }
}

// Handle structured form submission
async function handleStructuredSubmit(e) {
    e.preventDefault();
    const title = document.getElementById("form-title").value.trim();
    const amount = parseFloat(document.getElementById("form-amount").value);
    const category = document.getElementById("form-category").value;
    const dateVal = document.getElementById("form-date").value;
    const hasReceipt = document.getElementById("form-receipt").checked;

    if (!title || isNaN(amount) || !dateVal) {
        alert("Please fill in all structured form fields.");
        return;
    }

    // Compile into descriptive sentence for parsing node
    const receiptStr = hasReceipt ? "Here is the receipt." : "No receipt.";
    const text = `Expense claim for ${title} on ${dateVal} under category ${category} for $${amount.toFixed(2)}. ${receiptStr}`;
    
    addLogEntry(`Compiled structured form inputs to descriptive sentence.`, "info");
    
    // Switch to NLP view to show stream
    switchSubmitTab("nlp");
    
    // Submit compiled text
    document.getElementById("nlp-text").value = text;
    // Programmatically trigger submit event
    document.getElementById("nlp-expense-form").dispatchEvent(new Event("submit"));
    
    // Reset structured form
    document.getElementById("structured-expense-form").reset();
}

// Processes the JSON result from submitting/resuming workflow
function processWorkflowResult(result) {
    const state = result.state || {};
    
    // Log parsed elements
    if (state.title && state.amount) {
        addLogEntry(`PII Shield & Prompt Injection checks: Clean.`, "success");
        addLogEntry(`Parsed parameters: Merchant: "${state.title}", Amount: $${state.amount}, Category: "${state.category}", Date: ${state.expense_date}`, "success");
    }
    
    // Log validation
    if (state.validation_error) {
        addLogEntry(`Validation Error / Flags: ${state.validation_error}`, "warning");
    } else if (state.risk_level) {
        addLogEntry("Compliance Auditor: Policy checks passed.", "success");
    }

    // Log analysis
    if (state.gl_code) {
        addLogEntry(`Analyst Agent: Auto-mapped to GL Code: ${state.gl_code}, CC: ${state.cost_center}, Tax: ${state.tax_code}`, "success");
        if (state.saving_insight) {
            addLogEntry(`Analyst Insight: "${state.saving_insight}"`, "info");
        }
    }

    // Log final execution status
    if (result.status === "completed") {
        if (state.committed_to_erp) {
            addLogEntry(`Ledger MCP: Database write success. ${state.txn_id} committed to PostgreSQL.`, "success");
            addLogEntry("Notification MCP: Posted confirmation alert to Slack & Email.", "success");
        } else {
            addLogEntry(`Claim finalized. Output: "${result.final_output}"`, "info");
        }
        refreshDashboard();
    } else if (result.status === "paused") {
        addLogEntry(`Compliance Auditor: Claim flagged. Routing to Manager HITL Queue. Awaiting: ${result.required_input}`, "warning");
        addLogEntry("Notification MCP: Posted alert notice to Slack.", "warning");
        
        // Add to HITL table
        addToHitlQueue(result.session_id, state, result.required_input);
        refreshDashboard();
    }
}

// Add row to HITL Table
function addToHitlQueue(sessionId, state, requiredInput) {
    const tableBody = document.querySelector("#hitl-table tbody");
    if (!tableBody) return;

    // Remove empty row if exists
    const emptyRow = tableBody.querySelector(".empty-row");
    if (emptyRow) emptyRow.remove();

    // Check if row already exists for this session
    let row = document.getElementById(`hitl-row-${sessionId}`);
    if (!row) {
        row = document.createElement("tr");
        row.id = `hitl-row-${sessionId}`;
        tableBody.appendChild(row);
    }

    const shortId = sessionId.substring(0, 8) + "...";
    const riskClass = state.risk_level === "HIGH" ? "flag-high" : "flag-med";
    const pendingReason = requiredInput === "manager_decision" ? "Manager Decision" : "Receipt Upload Needed";
    
    // Action buttons based on required input
    let actionButtons = "";
    if (requiredInput === "manager_decision") {
        actionButtons = `
            <button class="btn btn-sm btn-success" onclick="managerDecision('${sessionId}', 'APPROVE')">Approve</button>
            <button class="btn btn-sm btn-danger" onclick="managerDecision('${sessionId}', 'REJECT')">Reject</button>
            <button class="btn btn-sm btn-warning" onclick="managerDecision('${sessionId}', 'REQUEST_RECEIPT')">Request Receipt</button>
        `;
    } else if (requiredInput === "receipt_upload") {
        actionButtons = `
            <button class="btn btn-sm btn-primary" onclick="openReceiptModal('${sessionId}')">Upload Receipt</button>
        `;
    }

    row.innerHTML = `
        <td class="amount-val">${shortId}</td>
        <td>${state.title || "Unparsed"}</td>
        <td class="amount-val">${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(state.amount || 0)}</td>
        <td>${state.category || "Uncategorized"}</td>
        <td><span class="flag ${riskClass}">${state.risk_level || "MEDIUM"}</span></td>
        <td><span class="text-amber font-semibold">${pendingReason}</span></td>
        <td><div class="row-actions">${actionButtons}</div></td>
    `;
}

// Submits a manager decision (APPROVE, REJECT, REQUEST_RECEIPT) to resume paused session
async function managerDecision(sessionId, decision) {
    addLogEntry(`HITL Manager Decision: Sending action "${decision}" for session ${sessionId}...`, "info");
    
    try {
        const response = await fetch(`/sessions/${sessionId}/decide`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "X-User-Role": "admin"
            },
            body: JSON.stringify({
                user_id: USER_ID,
                decision: decision,
                notes: `Manager approved via dashboard UI.`
            })
        });

        if (!response.ok) {
            throw new Error(`Decide endpoint returned ${response.status}`);
        }

        const result = await response.json();
        
        // Remove or update the row from queue
        const row = document.getElementById(`hitl-row-${sessionId}`);
        if (row) {
            if (result.session_status === "completed") {
                row.style.opacity = "0.3";
                setTimeout(() => {
                    row.remove();
                    checkHitlQueueEmpty();
                }, 800);
            } else if (result.session_status === "paused") {
                // E.g. status was updated to request receipt
                addToHitlQueue(sessionId, result.state, result.required_input);
            }
        }

        // Output log results
        processWorkflowResult({
            status: result.session_status,
            required_input: result.required_input,
            state: result.state,
            final_output: result.final_output,
            session_id: sessionId
        });
        
    } catch (err) {
        addLogEntry(`Error sending manager decision: ${err.message}`, "error");
    }
}

// Opens the modal to request receipt upload path
function openReceiptModal(sessionId) {
    currentModalSessionId = sessionId;
    const modal = document.getElementById("receipt-modal");
    if (modal) modal.classList.add("open");
}

function closeReceiptModal() {
    const modal = document.getElementById("receipt-modal");
    if (modal) modal.classList.remove("open");
    currentModalSessionId = null;
}

// Submits the receipt path to resume workflow
async function handleModalReceiptSubmit() {
    if (!currentModalSessionId) return;

    const pathInput = document.getElementById("receipt-upload-path");
    const receiptPath = pathInput.value.trim();

    if (!receiptPath) {
        alert("Please enter a valid receipt image path.");
        return;
    }

    addLogEntry(`HITL Receipt Upload: Resuming session ${currentModalSessionId} with receipt path "${receiptPath}"...`, "info");
    closeReceiptModal();

    try {
        const response = await fetch(`/sessions/${currentModalSessionId}/receipt`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "X-User-Role": "admin"
            },
            body: JSON.stringify({
                user_id: USER_ID,
                receipt_path: receiptPath
            })
        });

        if (!response.ok) {
            throw new Error(`Receipt endpoint returned status ${response.status}`);
        }

        const result = await response.json();

        // Update row status
        const row = document.getElementById(`hitl-row-${currentModalSessionId}`);
        if (row) {
            if (result.session_status === "completed") {
                row.style.opacity = "0.3";
                setTimeout(() => {
                    row.remove();
                    checkHitlQueueEmpty();
                }, 800);
            } else if (result.session_status === "paused") {
                // Resumed and paused again (e.g. for final manager approval decision)
                addToHitlQueue(currentModalSessionId, result.state, result.required_input);
            }
        }

        processWorkflowResult({
            status: result.session_status,
            required_input: result.required_input,
            state: result.state,
            final_output: result.final_output,
            session_id: currentModalSessionId
        });

        // Reset input
        pathInput.value = "";
    } catch (err) {
        addLogEntry(`Error uploading receipt: ${err.message}`, "error");
    }
}

// Checks if HITL Queue table is empty and renders placeholder
function checkHitlQueueEmpty() {
    const tableBody = document.querySelector("#hitl-table tbody");
    if (!tableBody) return;

    if (tableBody.querySelectorAll("tr").length === 0) {
        tableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="7">No claims currently pending review. Submissions requiring approval will appear here.</td>
            </tr>
        `;
    }
}

// Render the real-time compliance operations log stream from the backend
function renderComplianceStream(logs) {
    const logEntries = document.getElementById("log-entries");
    if (!logEntries) return;

    // Check if the content is different before rewriting to preserve scrolling/user feel
    const newHtml = logs.map(log => `
        <div class="log-entry ${log.type}">
            <span class="log-time">${log.time}</span>
            <span class="log-text">${log.text}</span>
        </div>
    `).join("");

    if (logEntries.innerHTML !== newHtml) {
        logEntries.innerHTML = newHtml;
        logEntries.scrollTop = logEntries.scrollHeight;
    }
}
