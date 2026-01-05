/**
 * Frontend Logic for Proxy Teacher System
 * OPTIMIZED VERSION
 * Expert Notes: Implements DocumentFragment for O(1) DOM reflows and strictly typed logic flow.
 */

"use strict";

class ProxyTeacherSystem {
    constructor() {
        // --- Configuration ---
        this.API_BASE = "http://127.0.0.1:5000/api";
        
        // --- State Management ---
        this.state = {
            proxyKey: localStorage.getItem("proxyKey") || "",
            pendingLectureId: null,
            isProcessing: false, // Concurrency Lock
            // Optimization: Cache active timeouts to clear them if needed
            toastTimeout: null 
        };

        // --- DOM Cache ---
        // We cache these once to avoid O(n) DOM searching repeatedly
        this.elements = {
            loginView: document.getElementById("login-view"),
            appView: document.getElementById("app-view"),
            keyInput: document.getElementById("proxy-key"),
            reasonInput: document.getElementById("claim-reason"),
            
            sections: {
                dashboard: document.getElementById("dashboard-section"),
                claims: document.getElementById("claims-section"),
                timetable: document.getElementById("timetable-section")
            },
            
            tables: {
                dashboard: document.querySelector("#dashboard-table tbody"),
                claims: document.querySelector("#claims-table tbody"),
                timetable: document.getElementById("timetable-table") // keeping ref to table, will query body later
            },
            
            emptyMsg: {
                dashboard: document.getElementById("dashboard-empty"),
                claims: document.getElementById("claims-empty"),
                timetable: document.getElementById("timetable-empty")
            },

            navButtons: document.querySelectorAll(".nav-btn"),
            loginBtn: document.getElementById("btn-login"),
            logoutBtn: document.getElementById("btn-logout"),
            loginError: document.getElementById("login-error"),
            
            modal: document.getElementById("claim-modal"),
            btnConfirmClaim: document.getElementById("btn-confirm-claim"),
            btnCancelModal: document.getElementById("btn-cancel-modal"),
            
            sidebar: document.getElementById("sidebar"),
            overlay: document.getElementById("sidebar-overlay"),
            btnMenu: document.getElementById("btn-menu"),
            btnCloseSidebar: document.getElementById("btn-close-sidebar"),
            
            toast: document.getElementById("toast"),
            displayUser: document.getElementById("display-user"),
            displayDate: document.getElementById("display-date")
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        if (this.state.proxyKey) {
            this.enterApp();
        } else {
            this.showLogin();
        }
    }

    // --- Event Listeners ---
    setupEventListeners() {
        const e = this.elements;

        // Bind methods once to preserve 'this' context and memory
        e.loginBtn.addEventListener("click", () => this.handleLogin());
        e.keyInput.addEventListener("keypress", (ev) => {
            if (ev.key === "Enter") this.handleLogin();
        });

        e.logoutBtn.addEventListener("click", () => this.handleLogout());

        // Delegation for nav buttons handled via NodeList iteration
        e.navButtons.forEach(btn => {
            btn.addEventListener("click", (ev) => this.switchTab(ev.currentTarget));
        });

        // Dashboard Refreshers
        document.getElementById("refresh-dashboard")?.addEventListener("click", () => this.loadDashboard());
        document.getElementById("refresh-claims")?.addEventListener("click", () => this.loadClaims());
        document.getElementById("refresh-timetable")?.addEventListener("click", () => this.loadTimetable());

        // Modal
        e.btnCancelModal.addEventListener("click", () => this.closeModal());
        e.btnConfirmClaim.addEventListener("click", () => this.submitClaim());
        e.reasonInput.addEventListener("keypress", (ev) => {
            if (ev.key === "Enter") this.submitClaim();
        });

        // Sidebar
        e.btnMenu.addEventListener("click", () => this.toggleSidebar(true));
        e.btnCloseSidebar.addEventListener("click", () => this.toggleSidebar(false));
        e.overlay.addEventListener("click", () => this.toggleSidebar(false));
    }

    // ============================================================
    // API SERVICE
    // ============================================================
    async _apiRequest(endpoint, method = "GET", body = null) {
        const options = {
            method,
            headers: { "Content-Type": "application/json" }
        };
        if (body) options.body = JSON.stringify(body);

        try {
            const response = await fetch(`${this.API_BASE}${endpoint}`, options);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error("API Error:", error);
            throw error; 
        }
    }

    // ============================================================
    // AUTHENTICATION
    // ============================================================
    async handleLogin() {
        if (this.state.isProcessing) return;
        
        const key = this.elements.keyInput.value.trim();
        if (!key) return this.showError("Please enter a teacher key.");

        this.setLoadingState(true, this.elements.loginBtn);

        try {
            const data = await this._apiRequest("/login", "POST", { proxy_key: key });
            if (data.success) {
                this.state.proxyKey = key;
                localStorage.setItem("proxyKey", key);
                this.enterApp();
            } else {
                this.showError(data.message);
            }
        } catch (err) {
            this.showError("Server unreachable.");
        } finally {
            this.setLoadingState(false, this.elements.loginBtn);
        }
    }

    handleLogout() {
        this.state.proxyKey = "";
        localStorage.removeItem("proxyKey");
        this.toggleSidebar(false);
        this.showLogin();
    }

    // ============================================================
    // UI LOGIC
    // ============================================================
    showLogin() {
        this.elements.loginView.classList.remove("hidden");
        this.elements.appView.classList.add("hidden");
        this.elements.keyInput.value = "";
        this.elements.loginError.textContent = "";
    }

    enterApp() {
        this.elements.loginView.classList.add("hidden");
        this.elements.appView.classList.remove("hidden");

        this.elements.displayUser.textContent = this.state.proxyKey;
        this.elements.displayDate.textContent = new Date().toLocaleDateString("en-US", { 
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
        });

        // Initialize default view
        const dashboardBtn = document.querySelector('.nav-btn[data-target="dashboard-section"]');
        if (dashboardBtn) this.switchTab(dashboardBtn);
        else this.loadDashboard(); // Fallback
    }

    switchTab(btn) {
        if (!btn) return;

        // 1. Update Buttons
        this.elements.navButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        // 2. Switch Sections (Fast DOM toggle)
        const targetId = btn.getAttribute("data-target");
        Object.values(this.elements.sections).forEach(s => {
            if (s.id === targetId) {
                s.classList.remove("hidden-section");
                s.classList.add("active-section");
            } else {
                s.classList.add("hidden-section");
                s.classList.remove("active-section");
            }
        });

        if (window.innerWidth <= 768) this.toggleSidebar(false);

        // 3. Load Data
        if (targetId === "dashboard-section") this.loadDashboard();
        else if (targetId === "claims-section") this.loadClaims();
        else if (targetId === "timetable-section") this.loadTimetable();
    }

    toggleSidebar(isOpen) {
        const { sidebar, overlay } = this.elements;
        if (isOpen) {
            sidebar.classList.add("open");
            overlay.classList.remove("hidden");
        } else {
            sidebar.classList.remove("open");
            overlay.classList.add("hidden");
        }
    }

    // ============================================================
    // DATA LOADING (DASHBOARD & CLAIMS)
    // ============================================================
    async loadDashboard() {
        const tbody = this.elements.tables.dashboard;
        this.renderLoading(tbody, 6);
        
        try {
            const data = await this._apiRequest("/dashboard");
            const records = data.data || [];
            
            this.toggleEmptyState(this.elements.emptyMsg.dashboard, tbody, records.length === 0);
            
            this.renderGenericTable(
                tbody, 
                records, 
                "dashboard", 
                ["Time", "Department", "ClassOrLab", "Subject", "TeacherDisplay"]
            );
        } catch (e) {
            this.showToast("Connection error");
            tbody.innerHTML = `<tr><td colspan="6" class="text-error">Could not load dashboard</td></tr>`;
        }
    }

    async loadClaims() {
        const tbody = this.elements.tables.claims;
        this.renderLoading(tbody, 5);
        
        try {
            const data = await this._apiRequest(`/my-claims?proxy_key=${this.state.proxyKey}`);
            const records = data.data || [];

            this.toggleEmptyState(this.elements.emptyMsg.claims, tbody, records.length === 0);

            this.renderGenericTable(
                tbody, 
                records, 
                "claims", 
                ["Time", "ClassOrLab", "Subject", "ClaimTime", "Status"]
            );
        } catch (e) {
            this.showToast("Could not load claims");
            tbody.innerHTML = "";
        }
    }

    // ============================================================
    // TIMETABLE (COMPLEX RENDER)
    // ============================================================
    async loadTimetable() {
        const table = this.elements.tables.timetable;
        const tbody = table.querySelector("tbody");
        const thead = table.querySelector("thead");

        tbody.innerHTML = "<tr><td colspan='5' style='text-align:center; padding:20px;'>Loading...</td></tr>";

        try {
            const data = await this._apiRequest(`/my-timetable?proxy_key=${this.state.proxyKey}`);
            const records = data.data || [];

            // Clear previous
            tbody.innerHTML = "";
            thead.innerHTML = "";

            if (records.length === 0) {
                this.elements.emptyMsg.timetable.classList.remove("hidden");
                return;
            }

            this.elements.emptyMsg.timetable.classList.add("hidden");

            // Build Header
            thead.innerHTML = `
                <tr>
                    <th style="width: 15%">Time</th>
                    <th style="width: 10%">Type</th>
                    <th style="width: 25%">Subject</th>
                    <th style="width: 20%">Location</th>
                    <th style="width: 30%">Details</th>
                </tr>
            `;

            // Optimization: Use DocumentFragment for O(1) Reflow
            const fragment = document.createDocumentFragment();

            records.forEach(row => {
                const tr = document.createElement("tr");
                const isProxy = row.Type === "Proxy";

                if (isProxy) {
                    tr.style.backgroundColor = "#FFFBEB"; 
                    tr.style.borderLeft = "4px solid #F59E0B"; 
                }

                // Internal helper for cell creation
                const addCell = (content, styleCb) => {
                    const td = document.createElement("td");
                    if (content instanceof HTMLElement) td.appendChild(content);
                    else td.textContent = content || "-";
                    if (styleCb) styleCb(td);
                    tr.appendChild(td);
                };

                addCell(row.Time, (td) => td.style.fontWeight = "600");

                // Badge Logic
                const badge = document.createElement("span");
                badge.className = isProxy ? "badge warning" : "badge";
                // Inline styles for specificity, can also be moved to CSS class
                if(isProxy) { badge.style.backgroundColor = "#F59E0B"; badge.style.color = "white"; }
                else { badge.style.backgroundColor = "#E5E7EB"; badge.style.color = "#374151"; }
                badge.textContent = isProxy ? "PROXY" : "REGULAR";
                addCell(badge);

                addCell(row.Subject);
                addCell(row.ClassOrLab);
                addCell(row.Details, (td) => {
                    td.style.color = "var(--text-muted)";
                    td.style.fontSize = "0.9rem";
                });

                fragment.appendChild(tr);
            });

            // Single DOM insertion
            tbody.appendChild(fragment);

        } catch (e) {
            this.showToast("Error loading timetable");
            tbody.innerHTML = "<tr><td colspan='5' style='text-align:center;'>Failed to load.</td></tr>";
        }
    }

    // ============================================================
    // ACTION HANDLERS
    // ============================================================
    openClaimModal(lectureId) {
        this.state.pendingLectureId = lectureId;
        this.elements.reasonInput.value = "";
        this.elements.modal.classList.remove("hidden");
        // Small timeout ensures focus works after transition
        setTimeout(() => this.elements.reasonInput.focus(), 50);
    }

    closeModal() {
        this.elements.modal.classList.add("hidden");
        this.state.pendingLectureId = null;
    }

    async submitClaim() {
        if (this.state.isProcessing) return;

        const reason = this.elements.reasonInput.value.trim();
        if (!reason) {
            alert("Please enter a reason.");
            return;
        }

        this.setLoadingState(true, this.elements.btnConfirmClaim);

        try {
            const payload = {
                proxy_key: this.state.proxyKey,
                lecture_id: this.state.pendingLectureId,
                reason: reason
            };
            const data = await this._apiRequest("/claim", "POST", payload);

            if (data.success) {
                this.showToast("Claim Successful!");
                this.closeModal();
                // Parallel refresh for speed
                this.loadDashboard();
                this.loadClaims();
            } else {
                alert(data.message);
            }
        } catch (e) {
            alert("Claim failed.");
        } finally {
            this.setLoadingState(false, this.elements.btnConfirmClaim);
        }
    }

    async cancelClaim(claimId) {
        if (!confirm("Cancel this claim?")) return;
        
        try {
            const data = await this._apiRequest("/cancel", "POST", {
                proxy_key: this.state.proxyKey,
                claim_id: claimId
            });

            if (data.success) {
                this.showToast("Claim cancelled.");
                this.loadClaims();
                this.loadDashboard();
            } else {
                alert(data.message);
            }
        } catch (e) {
            alert("Cancellation failed.");
        }
    }

    // ============================================================
    // RENDERING ENGINE
    // ============================================================

    /**
     * Highly optimized table renderer using DocumentFragment
     */
    renderGenericTable(tbody, data, type, columns) {
        tbody.innerHTML = "";
        if (!Array.isArray(data)) return;

        // Create a fragment in memory (Time Complexity Optimization)
        const fragment = document.createDocumentFragment();

        data.forEach((row, index) => {
            const tr = document.createElement("tr");

            columns.forEach(colKey => {
                const td = document.createElement("td");
                if (colKey === "Status") {
                    const status = (row["Status"] || "active").toLowerCase();
                    const badge = document.createElement("span");
                    badge.className = `badge ${status}`;
                    badge.textContent = status;
                    td.appendChild(badge);
                } else {
                    td.textContent = row[colKey] || "-";
                }
                tr.appendChild(td);
            });

            // Action Column
            const tdAction = document.createElement("td");
            const actionBtn = this._createActionButton(type, row, index);
            if (actionBtn) tdAction.appendChild(actionBtn);
            else if (type === "claims") tdAction.textContent = "-";

            tr.appendChild(tdAction);
            fragment.appendChild(tr);
        });

        // One single reflow for the whole table
        tbody.appendChild(fragment);
    }

    /**
     * Helper to separate button logic from render loop (Encapsulation)
     */
    _createActionButton(type, row, index) {
        if (type === "dashboard") {
            const btn = document.createElement("button");
            btn.className = "btn-primary";
            btn.style.cssText = "padding: 6px 12px; font-size: 0.8rem;";
            btn.textContent = "Claim";
            const id = (row.lecture_id !== undefined) ? row.lecture_id : index;
            btn.onclick = () => this.openClaimModal(id);
            return btn;
        } 
        else if (type === "claims") {
            if ((row["Status"] || "active").toLowerCase() === "active") {
                const btn = document.createElement("button");
                btn.className = "btn-danger";
                btn.textContent = "Cancel";
                const cid = (typeof row.claim_id !== "undefined") ? row.claim_id : index;
                btn.onclick = () => this.cancelClaim(cid);
                return btn;
            }
        }
        return null;
    }

    renderLoading(element, cols) {
        element.innerHTML = `<tr><td colspan="${cols}" style="text-align:center; padding: 20px;">Loading data...</td></tr>`;
    }

    toggleEmptyState(emptyDiv, tableBody, isEmpty) {
        if (isEmpty) {
            emptyDiv.classList.remove("hidden");
            if (tableBody && tableBody.parentElement) {
                tableBody.parentElement.classList.add("hidden");
            }
        } else {
            emptyDiv.classList.add("hidden");
            if (tableBody && tableBody.parentElement) {
                tableBody.parentElement.classList.remove("hidden");
            }
        }
    }

    // ============================================================
    // UTILITIES
    // ============================================================
    
    showError(msg) {
        this.elements.loginError.textContent = msg;
    }

    showToast(msg) {
        const t = this.elements.toast;
        t.textContent = msg;
        t.classList.remove("hidden");
        
        // Memory leak prevention: clear existing timeout
        if (this.state.toastTimeout) clearTimeout(this.state.toastTimeout);
        
        this.state.toastTimeout = setTimeout(() => {
            t.classList.add("hidden");
            this.state.toastTimeout = null;
        }, 3000);
    }

    setLoadingState(isLoading, buttonElement) {
        this.state.isProcessing = isLoading;
        if (buttonElement) {
            buttonElement.disabled = isLoading;
            buttonElement.style.opacity = isLoading ? "0.7" : "1";
            buttonElement.style.cursor = isLoading ? "not-allowed" : "pointer";
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.proxySystem = new ProxyTeacherSystem();
});