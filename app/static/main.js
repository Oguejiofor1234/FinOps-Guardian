document.addEventListener("DOMContentLoaded", () => {
    const expenseForm = document.getElementById("expense-form");
    const logEntries = document.getElementById("log-entries");
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("receipt-file");
    const hitlBody = document.querySelector(".hitl-table tbody");

    // File Drag & Drop Interactivity
    dropzone.addEventListener("click", () => fileInput.click());
    
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--clr-primary)";
        dropzone.style.background = "rgba(14, 165, 233, 0.05)";
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.style.borderColor = "var(--clr-border)";
        dropzone.style.background = "transparent";
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--clr-border)";
        dropzone.style.background = "transparent";
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0]);
        }
    });

    function handleFileSelect(file) {
        const textSpan = dropzone.querySelector(".dropzone-text");
        textSpan.textContent = `Attached: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        dropzone.style.borderColor = "var(--clr-success)";
    }

    // Helper to log event to stream
    function addLogEntry(text, type = "info") {
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

    // Process Form Submissions (Simulate Agent Pipeline)
    expenseForm.addEventListener("submit", (e) => {
        e.preventDefault();
        
        const title = document.getElementById("title").value;
        const amount = parseFloat(document.getElementById("amount").value);
        const category = document.getElementById("category").value;
        const dateVal = document.getElementById("date").value;
        
        const parsedDate = new Date(dateVal);
        const isWeekend = parsedDate.getDay() === 5 || parsedDate.getDay() === 6; // Fri or Sat in UTC/local index checks

        addLogEntry(`Ingesting claim: "${title}" - $${amount.toFixed(2)}`, "info");

        // Step 1: Guardrails
        setTimeout(() => {
            addLogEntry("Guardrails active: Scanning input text for sensitive data...", "info");
        }, 800);

        setTimeout(() => {
            // Mock PII check
            if (title.match(/\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/)) {
                addLogEntry("PII Shield: Redacted credit card number from expense title.", "warning");
            } else {
                addLogEntry("PII Shield & Prompt Injection checks: Clean.", "success");
            }
        }, 1600);

        // Step 2: Auditor Agent Policy checks
        setTimeout(() => {
            addLogEntry("Compliance Auditor: running expense policy checks...", "info");
        }, 2400);

        setTimeout(() => {
            let auditFailed = false;
            let flags = [];

            if (category === "meals" && amount > 75.00) {
                flags.push("Exceeded Meals limit ($75)");
                addLogEntry(`Policy Alert: Meals expense exceeds daily limit of $75.00.`, "warning");
                auditFailed = true;
            }

            if (category === "software" && amount > 500.00) {
                flags.push("Software exceeds $500 limit");
                addLogEntry(`Policy Alert: Software subscription exceeds limit of $500.00.`, "warning");
                auditFailed = true;
            }

            if (isWeekend) {
                flags.push("Weekend Expense");
                addLogEntry(`Policy Alert: Expense incurred on weekend. Flagging for review.`, "warning");
                auditFailed = true;
            }

            if (auditFailed) {
                addLogEntry("Compliance Auditor: Audit failed. Routing claim to Manager HITL Queue.", "error");
                addLogEntry("Notification MCP: Sending Slack alert and Email to Finance Reviewers.", "warning");
                
                // Add to HITL Table dynamically
                const claimId = `CLAIM-${Math.floor(Math.random() * 900) + 100}`;
                const newRow = document.createElement("tr");
                newRow.innerHTML = `
                    <td>${claimId}</td>
                    <td>Employee Session</td>
                    <td>${title}</td>
                    <td class="amount-val">$${amount.toFixed(2)}</td>
                    <td>${flags.map(f => `<span class="flag flag-high">${f}</span>`).join(" ")}</td>
                    <td>
                        <button class="btn btn-sm btn-success">Approve</button>
                        <button class="btn btn-sm btn-danger">Reject</button>
                    </td>
                `;
                hitlBody.appendChild(newRow);
                setupTableRowListeners(newRow, claimId, title, amount);
            } else {
                // Success Path: Analyst maps tax
                addLogEntry("Compliance Auditor: All policy checks passed.", "success");
                addLogEntry("Analyst Agent: Mapping tax codes...", "info");
                
                setTimeout(() => {
                    let taxCode = "GEN-TAX";
                    if (category === "meals") taxCode = "ME-50";
                    else if (category === "travel") taxCode = "TRV-100";
                    else if (category === "office") taxCode = "OFF-100";
                    else if (category === "software") taxCode = "SaaS-100";

                    addLogEntry(`Analyst Agent: Successfully mapped to Tax Code ${taxCode}.`, "success");
                    addLogEntry("Ledger MCP: Writing record to PostgreSQL Ledger...", "info");
                    
                    setTimeout(() => {
                        addLogEntry(`Ledger MCP: Database write success. TXN-POSTGRES-${Math.floor(Math.random() * 9000) + 1000} committed.`, "success");
                        addLogEntry("Notification MCP: Sending Slack confirmation alert.", "success");
                    }, 800);
                }, 800);
            }
        }, 3200);

        // Reset form
        expenseForm.reset();
        const textSpan = dropzone.querySelector(".dropzone-text");
        textSpan.textContent = "Drag receipt image here or click to browse";
        dropzone.style.borderColor = "var(--clr-border)";
    } catch(err) {
        console.error(err);
    }
    });

    // Listeners for HITL actions
    function setupTableRowListeners(row, claimId, title, amount) {
        const approveBtn = row.querySelector(".btn-success");
        const rejectBtn = row.querySelector(".btn-danger");

        approveBtn.addEventListener("click", () => {
            addLogEntry(`HITL Manager Approval: Claim ${claimId} approved manually.`, "success");
            addLogEntry(`Analyst Agent: Categorizing approved claim "${title}"...`, "info");
            
            setTimeout(() => {
                addLogEntry("Ledger MCP: Committing approved claim to PostgreSQL ERP database.", "success");
                row.style.opacity = "0.3";
                approveBtn.disabled = true;
                rejectBtn.disabled = true;
                setTimeout(() => row.remove(), 1000);
            }, 800);
        });

        rejectBtn.addEventListener("click", () => {
            addLogEntry(`HITL Manager Rejection: Claim ${claimId} rejected manually.`, "error");
            addLogEntry("Notification MCP: Sending Email alert containing rejection reasons to submitter.", "warning");
            row.style.opacity = "0.3";
            approveBtn.disabled = true;
            rejectBtn.disabled = true;
            setTimeout(() => row.remove(), 1000);
        });
    }

    // Setup initial listeners for statically defined rows
    const staticRows = document.querySelectorAll(".hitl-table tbody tr");
    staticRows.forEach((row, index) => {
        const claimId = row.cells[0].textContent;
        const title = row.cells[2].textContent;
        const amount = parseFloat(row.cells[3].textContent.replace("$", ""));
        setupTableRowListeners(row, claimId, title, amount);
    });
});
