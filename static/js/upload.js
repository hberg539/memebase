/* -- DOM refs -- */

const addBtn = document.getElementById("btn-add");
const addModal = document.getElementById("add-modal");
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const urlInput = document.getElementById("url-input");
const urlDownload = document.getElementById("url-download");

/* -- Add modal -- */

addBtn.addEventListener("click", () => {
	addModal.showModal();
	addModal.focus();
});
wireDialog(addModal, { cancel: "add-cancel" });

/* -- Drop zone -- */

dropZone.addEventListener("dragenter", (e) => {
	e.preventDefault();
	dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragover", (e) => {
	e.preventDefault();
});
dropZone.addEventListener("dragleave", (e) => {
	e.preventDefault();
	if (!dropZone.contains(e.relatedTarget)) {
		dropZone.classList.remove("drag-over");
	}
});
dropZone.addEventListener("drop", (e) => {
	e.preventDefault();
	dropZone.classList.remove("drag-over");
	const all = [...e.dataTransfer.files];
	const files = all.filter((f) => f.type.startsWith("image/") || f.type.startsWith("video/"));
	if (files.length < all.length) {
		const skipped = all.length - files.length;
		showAlert(`${skipped} unsupported file${skipped > 1 ? "s" : ""} skipped`, "warning");
	}
	if (files.length) uploadFiles(files);
});

/* -- File upload -- */

dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
	if (fileInput.files.length) uploadFiles([...fileInput.files]);
	fileInput.value = "";
});

async function uploadFiles(files) {
	const form = new FormData();
	files.forEach((f) => form.append("files", f));
	addModal.close();
	try {
		const uploaded = await Api.uploadFiles(form);
		const dupes = uploaded.filter((m) => m.duplicate);
		const freshMemes = uploaded.filter((m) => !m.duplicate);
		for (const m of freshMemes) showAlert(`Uploaded ${m.filename}`, "success");
		for (const m of dupes) showAlert(`${m.filename}: duplicate skipped`, "warning");
		currentPage = 1;
		await load(search.value);
		clearSelection();
		for (const m of uploaded) {
			const card = grid.querySelector(`.card[data-id="${m.id}"]`);
			if (card) {
				selectedIds.add(m.id);
				card.classList.add("selected");
			}
		}
		updateSelectBar();
	} catch (e) {
		showAlert(e.message || "Upload failed", "error");
	}
}

/* -- URL download -- */

urlDownload.addEventListener("click", async () => {
	const url = urlInput.value.trim();
	if (!url) return;
	urlDownload.disabled = true;
	urlDownload.textContent = "Downloading...";
	try {
		const memes = await Api.downloadUrl(url);
		addModal.close();
		urlInput.value = "";
		const dupes = memes.filter((m) => m.duplicate);
		const fresh = memes.filter((m) => !m.duplicate);
		for (const m of fresh) showAlert(`Downloaded ${m.filename}`, "success");
		for (const m of dupes) showAlert(`${m.filename}: duplicate skipped`, "warning");
		currentPage = 1;
		await load(search.value);
		clearSelection();
		for (const m of memes) {
			selectedIds.add(m.id);
			const card = grid.querySelector(`.card[data-id="${m.id}"]`);
			if (card) card.classList.add("selected");
		}
		updateSelectBar();
	} catch (e) {
		const isUnsupported = e.message?.includes("Unsupported file type");
		const isNoMedia = e.message?.includes("No supported media");
		showAlert(e.message, isUnsupported || isNoMedia ? "warning" : "error");
	} finally {
		urlDownload.disabled = false;
		urlDownload.textContent = "Download";
	}
});

/* -- Global drag-and-drop -- */

document.addEventListener("dragover", (e) => {
	e.preventDefault();
});
document.addEventListener("dragenter", (e) => {
	e.preventDefault();
	if (!addModal.open) {
		addModal.showModal();
		addModal.focus();
	}
	dropZone.classList.add("drag-over");
});
document.addEventListener("dragleave", (e) => {
	if (!e.relatedTarget || !document.contains(e.relatedTarget)) {
		dropZone.classList.remove("drag-over");
	}
});
document.addEventListener("drop", (e) => {
	dropZone.classList.remove("drag-over");
	if (e.target.closest("#drop-zone")) return; // let drop-zone handler handle it
	e.preventDefault();
	const all = [...e.dataTransfer.files];
	const files = all.filter((f) => f.type.startsWith("image/") || f.type.startsWith("video/"));
	if (files.length < all.length) {
		const skipped = all.length - files.length;
		showAlert(`${skipped} unsupported file${skipped > 1 ? "s" : ""} skipped`, "warning");
	}
	if (files.length) uploadFiles(files);
});

/* -- Clipboard paste upload -- */

document.addEventListener("paste", (e) => {
	const tag = document.activeElement?.tagName;
	if (tag === "INPUT" || tag === "TEXTAREA") return;
	const items = [...(e.clipboardData?.items || [])];
	const files = items
		.filter((item) => item.type.startsWith("image/"))
		.map((item) => item.getAsFile())
		.filter(Boolean)
		.map((file) => {
			const ext = file.type.split("/")[1] || "png";
			const ts = new Date().toISOString().replace(/[-:]/g, "").replace("T", "_").split(".")[0];
			return new File([file], `paste_${ts}.${ext}`, { type: file.type });
		});
	if (!files.length) return;
	e.preventDefault();
	uploadFiles(files);
});

load();
