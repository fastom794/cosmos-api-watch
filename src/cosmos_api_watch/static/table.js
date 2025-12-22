function filterTable() {
    const project = document.getElementById("filter-project").value;
    const networkType = document.getElementById("filter-network-type").value;
    const chainId = document.getElementById("filter-chain-id").value;
    const ntype = document.getElementById("filter-type").value;
    const enabled = document.getElementById("filter-enabled").value;
    const status = document.getElementById("filter-status").value;

    const rows = document.querySelectorAll("tbody tr");

    rows.forEach(row => {
        const projectVal = row.getAttribute("data-project");
        const networkTypeVal = row.getAttribute("data-network-type");
        const chainIdVal = row.getAttribute("data-chain-id");
        const typeVal = row.getAttribute("data-endpoint-type");
        const enabledVal = row.getAttribute("data-enabled");
        const statusVal = row.getAttribute("data-status");

        const show =
            (project === "" || project === projectVal) &&
            (networkType === "" || networkType === networkTypeVal) &&
            (chainId === "" || chainId === chainIdVal) &&
            (ntype === "" || ntype === typeVal) &&
            (enabled === "" || enabled === enabledVal) &&
            (status === "" || status === statusVal);

        row.style.display = show ? "" : "none";
    });
}

function initLastCheck() {
    const cells = document.querySelectorAll("td.last-check");
    const now = Date.now();

    cells.forEach(cell => {
        let iso = cell.getAttribute("data-last-checked");
        if (!iso) {
            cell.textContent = "";
            return;
        }

        // Force UTC
        if (!iso.endsWith("Z")) {
            iso = iso + "Z";
        }

        const t = Date.parse(iso);
        if (Number.isNaN(t)) {
            cell.textContent = "";
            return;
        }

        const diffSec = Math.floor((now - t) / 1000);
        cell.textContent = diffSec + " s ago";
    });
}


document.addEventListener("DOMContentLoaded", () => {
    initLastCheck();
    filterTable();
});

