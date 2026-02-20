/**
 * Amazon Price Tracker — Frontend Logic
 * Handles search requests, rendering results, and UI state management.
 */

const API_URL = "/api/search";

// ── DOM Elements ──
const searchBtn = document.getElementById("search-btn");
const searchQuery = document.getElementById("search-query");
const priceThreshold = document.getElementById("price-threshold");
const statusBar = document.getElementById("status-bar");
const statusText = document.getElementById("status-text");
const resultsSection = document.getElementById("results");
const resultsGrid = document.getElementById("results-grid");
const resultsCount = document.getElementById("results-count");
const emptyState = document.getElementById("empty-state");

// Stats
const statCountValue = document.getElementById("stat-count-value");
const statAlertValue = document.getElementById("stat-alert-value");
const statRangeValue = document.getElementById("stat-range-value");


// ── Format currency ──
function formatUSD(value) {
    if (!value || value <= 0) return "N/D";
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(value);
}


// ── Set loading state ──
function setLoading(loading) {
    if (loading) {
        searchBtn.classList.add("btn-search--loading");
        searchBtn.disabled = true;
    } else {
        searchBtn.classList.remove("btn-search--loading");
        searchBtn.disabled = false;
    }
}


// ── Show status bar ──
function showStatus(message, isError = false) {
    statusBar.hidden = false;
    statusText.textContent = message;
    statusBar.classList.toggle("status-bar--error", isError);

    // Update SVG icon
    const iconSvg = statusBar.querySelector(".status-bar__icon");
    if (isError) {
        iconSvg.innerHTML = '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>';
    } else {
        iconSvg.innerHTML = '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>';
    }
}


// ── Update stats cards ──
function updateStats(data) {
    statCountValue.textContent = data.count > 0 ? data.count : "—";
    statAlertValue.textContent = formatUSD(parseFloat(priceThreshold.value));
    statRangeValue.textContent =
        data.price_min && data.price_max
            ? `${formatUSD(data.price_min)} — ${formatUSD(data.price_max)}`
            : "—";
}


// ── Create a product card ──
function createProductCard(product, threshold, index) {
    const isDeal = product.price_usd && product.price_usd > 0 && product.price_usd < threshold;
    const card = document.createElement("article");
    card.className = "product-card";
    card.style.animationDelay = `${index * 50}ms`;

    // Click opens product page
    card.addEventListener("click", (e) => {
        if (e.target.closest("a")) return; // Don't double-navigate
        window.open(product.url, "_blank", "noopener");
    });

    card.innerHTML = `
        <div class="product-card__indicator ${isDeal ? "product-card__indicator--deal" : ""}"></div>
        <div class="product-card__body">
            <h3 class="product-card__title">${escapeHTML(product.title)}</h3>
            <div class="product-card__meta">
                <span class="product-card__tag ${product.ships_to_colombia ? "product-card__tag--shipping-yes" : "product-card__tag--shipping-no"}">
                    ${product.ships_to_colombia
                        ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg> Envio Colombia'
                        : "Sin envio confirmado"
                    }
                </span>
                ${isDeal ? '<span class="product-card__tag product-card__tag--shipping-yes">Bajo alerta</span>' : ""}
            </div>
        </div>
        <div class="product-card__price-section">
            <span class="product-card__price ${isDeal ? "product-card__price--deal" : ""}">
                ${product.price_usd && product.price_usd > 0 ? formatUSD(product.price_usd) : "N/D"}
            </span>
            <a class="product-card__link" href="${escapeAttr(product.url)}" target="_blank" rel="noopener noreferrer">
                Ver
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>
            </a>
        </div>
    `;

    return card;
}


// ── Escape HTML to prevent XSS ──
function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function escapeAttr(str) {
    return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}


// ── Render results ──
function renderResults(data) {
    const threshold = parseFloat(priceThreshold.value) || 750;

    if (data.products.length === 0) {
        resultsSection.hidden = true;
        emptyState.hidden = false;
        return;
    }

    emptyState.hidden = true;
    resultsSection.hidden = false;
    resultsGrid.innerHTML = "";
    resultsCount.textContent = `${data.products.length} productos`;

    data.products.forEach((product, i) => {
        const card = createProductCard(product, threshold, i);
        resultsGrid.appendChild(card);
    });
}


// ── Main search handler ──
async function handleSearch() {
    const query = searchQuery.value.trim();
    const threshold = parseFloat(priceThreshold.value) || 750;

    if (!query) {
        searchQuery.focus();
        return;
    }

    setLoading(true);
    statusBar.hidden = true;

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: query,
                price_threshold: threshold,
            }),
        });

        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status}`);
        }

        const data = await response.json();

        updateStats(data);
        renderResults(data);
        showStatus(data.status, data.count === 0);

    } catch (error) {
        console.error("Search error:", error);
        showStatus(`Error: ${error.message}`, true);
        updateStats({ count: 0, price_min: null, price_max: null });
    } finally {
        setLoading(false);
    }
}


// ── Event Listeners ──
searchBtn.addEventListener("click", handleSearch);

// Enter key triggers search
searchQuery.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSearch();
});

// Update threshold stat on change
priceThreshold.addEventListener("change", () => {
    statAlertValue.textContent = formatUSD(parseFloat(priceThreshold.value));
});
