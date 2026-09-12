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

function getMemeShareUrl(id, filename) {
	const relPath = `/memes/${id}/${encodeURIComponent(filename)}`;
	if (!window.PUBLIC_URL) {
		return `${window.location.origin}${relPath}`;
	}
	const base = window.PUBLIC_URL.replace(/\/+$/, "");
	if (base.endsWith("/memes")) {
		return `${base}/${id}/${encodeURIComponent(filename)}`;
	}
	return `${base}${relPath}`;
}

async function copyText(text, feedbackEl) {
	let copied = false;
	if (navigator.clipboard?.writeText) {
		try {
			await navigator.clipboard.writeText(text);
			copied = true;
		} catch (e) {
			console.warn("navigator.clipboard.writeText failed:", e);
		}
	}
	if (!copied) {
		const textarea = document.createElement("textarea");
		textarea.value = text;
		textarea.style.position = "fixed";
		textarea.style.top = "0";
		textarea.style.left = "0";
		textarea.style.width = "2em";
		textarea.style.height = "2em";
		textarea.style.padding = "0";
		textarea.style.border = "none";
		textarea.style.outline = "none";
		textarea.style.boxShadow = "none";
		textarea.style.background = "transparent";
		textarea.setAttribute("readonly", "");
		document.body.appendChild(textarea);
		textarea.focus();
		textarea.select();
		textarea.setSelectionRange(0, textarea.value.length);
		try {
			copied = document.execCommand("copy");
		} catch (e) {
			console.error("document.execCommand copy failed:", e);
		}
		document.body.removeChild(textarea);
	}

	if (feedbackEl) {
		const prev = feedbackEl.innerHTML;
		const isShareCopy = feedbackEl.id === "m-copy-url";
		const iconSize = isShareCopy ? 14 : 18;
		const label = isShareCopy ? (copied ? " Copied!" : " Failed") : "";
		feedbackEl.innerHTML = icon(copied ? "check" : "x", iconSize) + label;
		feedbackEl.classList.add("copied");
		refreshIcons();
		setTimeout(() => {
			feedbackEl.innerHTML = prev;
			feedbackEl.classList.remove("copied");
			refreshIcons();
		}, 1000);
	}
}

/* -- Clipboard & download -- */

async function copyImage(src, feedbackEl) {
	const item = new ClipboardItem({
		"image/png": (async () => {
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
			if (!pngBlob) throw new Error("Failed to convert image");
			return pngBlob;
		})(),
	});
	await navigator.clipboard.write([item]);
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
