/* -- HTML helpers -- */

function esc(s) {
	const d = document.createElement("div");
	d.textContent = s;
	return d.innerHTML;
}

function icon(name, size = 16) {
	return `<i data-lucide="${name}" style="width:${size}px;height:${size}px"></i>`;
}

function refreshIcons() {
	lucide.createIcons();
}

/* -- File helpers -- */

function splitExt(fn) {
	const i = fn.lastIndexOf(".");
	return i === -1 ? [fn, ""] : [fn.slice(0, i), fn.slice(i)];
}

function normExt(filename) {
	const ext = filename.slice(filename.lastIndexOf(".") + 1).toLowerCase();
	return ext === "jpeg" ? "jpg" : ext;
}

const VIDEO_EXTS = [".webm", ".mp4"];
function isVideo(filename) {
	return VIDEO_EXTS.some((e) => filename.toLowerCase().endsWith(e));
}

const COPYABLE_EXTS = [".png", ".jpg", ".jpeg", ".webp"];
function canCopy(filename) {
	return (
		navigator.clipboard?.write && COPYABLE_EXTS.some((e) => filename.toLowerCase().endsWith(e))
	);
}

/* -- Clipboard & download -- */

async function copyImage(src, feedbackEl) {
	const res = await fetch(src);
	const blob = await res.blob();
	const img = new window.Image();
	img.crossOrigin = "anonymous";
	const url = URL.createObjectURL(blob);
	await new Promise((resolve, reject) => {
		img.onload = resolve;
		img.onerror = reject;
		img.src = url;
	});
	const c = document.createElement("canvas");
	c.width = img.naturalWidth;
	c.height = img.naturalHeight;
	c.getContext("2d").drawImage(img, 0, 0);
	URL.revokeObjectURL(url);
	const pngBlob = await new Promise((r) => c.toBlob(r, "image/png"));
	await navigator.clipboard.write([new ClipboardItem({ "image/png": pngBlob })]);
	if (feedbackEl) {
		const prev = feedbackEl.innerHTML;
		feedbackEl.innerHTML = icon("check", 18);
		feedbackEl.classList.add("copied");
		refreshIcons();
		setTimeout(() => {
			feedbackEl.innerHTML = prev;
			feedbackEl.classList.remove("copied");
			refreshIcons();
		}, 1000);
	}
}

function downloadFile(src, filename) {
	const a = document.createElement("a");
	a.href = src;
	a.download = filename;
	a.click();
}

/* -- Formatting -- */

function formatSize(bytes) {
	if (!bytes) return "";
	const units = ["B", "KB", "MB", "GB"];
	let i = 0;
	let size = bytes;
	while (size >= 1024 && i < units.length - 1) {
		size /= 1024;
		i++;
	}
	return `${i === 0 ? size : size.toFixed(1)}\u00a0${units[i]}`;
}

/* -- Dialog animation -- */

document.querySelectorAll("dialog").forEach((d) => {
	const origClose = d.close.bind(d);
	d.close = () => {
		if (!d.open) return;
		d.classList.add("closing");
		d.addEventListener(
			"transitionend",
			() => {
				d.classList.remove("closing");
				origClose();
			},
			{ once: true },
		);
		setTimeout(() => {
			d.classList.remove("closing");
			origClose();
		}, 200);
	};
});
