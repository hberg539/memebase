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
	dropZone.classList.remove("drag-over");
});
dropZone.addEventListener("drop", (e) => {
	e.preventDefault();
	dropZone.classList.remove("drag-over");
	const files = [...e.dataTransfer.files].filter(
		(f) => f.type.startsWith("image/") || f.type.startsWith("video/"),
	);
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
			const card = grid.querySelector(`.card[data-uuid="${m.uuid}"]`);
			if (card) {
				selectedUuids.add(m.uuid);
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
		const meme = await Api.downloadUrl(url);
		addModal.close();
		urlInput.value = "";
		currentPage = 1;
		await load(search.value);
		clearSelection();
		selectedUuids.add(meme.uuid);
		const card = grid.querySelector(`.card[data-uuid="${meme.uuid}"]`);
		if (card) card.classList.add("selected");
		updateSelectBar();
		showAlert(`Downloaded ${meme.filename}`, "success");
	} catch (e) {
		showAlert(e.message, "error");
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
	const files = [...e.dataTransfer.files].filter(
		(f) => f.type.startsWith("image/") || f.type.startsWith("video/"),
	);
	if (files.length) uploadFiles(files);
});

load();
