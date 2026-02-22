const toastContainer = document.createElement("div");
toastContainer.id = "toast-container";
toastContainer.popover = "manual";
document.body.appendChild(toastContainer);
toastContainer.showPopover();

const toastIcons = {
	success: "CircleCheck",
	error: "CircleX",
	warning: "TriangleAlert",
	info: "Info",
};

function showAlert(message, type = "info") {
	const toast = document.createElement("div");
	toast.className = `toast toast-${type}`;
	const iconName = toastIcons[type] || "Info";
	const svg = lucide.createElement(lucide.icons[iconName]);
	svg.setAttribute("width", "16");
	svg.setAttribute("height", "16");
	const span = document.createElement("span");
	span.textContent = message;
	toast.appendChild(svg);
	toast.appendChild(span);
	toast.addEventListener("click", () => dismissToast(toast));
	toastContainer.prepend(toast);
	// Re-promote to top of top layer so it's above any open dialog
	toastContainer.hidePopover();
	toastContainer.showPopover();
	requestAnimationFrame(() => toast.classList.add("toast-visible"));

	// Max 10 visible
	const toasts = toastContainer.querySelectorAll(".toast:not(.toast-hiding)");
	if (toasts.length > 10) dismissToast(toasts[0]);

	setTimeout(() => dismissToast(toast), 7000);
}

function dismissToast(toast) {
	if (toast.classList.contains("toast-hiding")) return;
	toast.classList.add("toast-hiding");
	toast.classList.remove("toast-visible");
	toast.addEventListener("transitionend", () => toast.remove(), { once: true });
	setTimeout(() => toast.remove(), 500);
}
