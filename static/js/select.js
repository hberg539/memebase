/* -- State -- */

const selectedIds = new Set();
const selectBar = document.getElementById("select-bar");
const selCount = document.getElementById("sel-count");

/* -- Selection management -- */

function updateSelectBar() {
	const n = selectedIds.size;
	selCount.textContent = `${n} selected`;
	selectBar.classList.toggle("visible", n > 0);
}

function restoreSelection() {
	grid.querySelectorAll(".card").forEach((c) => {
		if (selectedIds.has(c.dataset.id)) c.classList.add("selected");
	});
}

function clearSelection() {
	selectedIds.clear();
	grid.querySelectorAll(".card.selected").forEach((c) => c.classList.remove("selected"));
	updateSelectBar();
}

/* -- Shift+click selection -- */

grid.addEventListener(
	"click",
	(e) => {
		if (!e.shiftKey) return;
		const card = e.target.closest(".card");
		if (!card) return;
		e.preventDefault();
		e.stopPropagation();
		const id = card.dataset.id;
		if (selectedIds.has(id)) {
			selectedIds.delete(id);
			card.classList.remove("selected");
		} else {
			selectedIds.add(id);
			card.classList.add("selected");
		}
		updateSelectBar();
		resetSelDelete();
	},
	true,
);

/* -- Selection bar buttons -- */

document.getElementById("sel-all").addEventListener("click", () => {
	grid.querySelectorAll(".card").forEach((c) => {
		selectedIds.add(c.dataset.id);
		c.classList.add("selected");
	});
	updateSelectBar();
	resetSelDelete();
});

document.getElementById("sel-clear").addEventListener("click", clearSelection);

document.addEventListener("keydown", (e) => {
	if (e.key === "Escape" && selectedIds.size && !anyDialogOpen()) {
		clearSelection();
	}
});

/* -- Bulk delete -- */

const selDelBtn = document.getElementById("sel-delete");
const resetSelDelete = confirmButton(
	selDelBtn,
	() => `Delete ${selectedIds.size}?`,
	async () => {
		const count = selectedIds.size;
		try {
			const promises = [...selectedIds].map((id) => Api.deleteMeme(id));
			await Promise.all(promises);
			showAlert(`Deleted ${count} meme${count > 1 ? "s" : ""}`, "success");
			selectedIds.forEach((id) => {
				const card = grid.querySelector(`.card[data-id="${id}"]`);
				if (card) card.classList.add("removing");
			});
			await new Promise((r) => setTimeout(r, 200));
		} catch (e) {
			showAlert(e.message || "Delete failed", "error");
		}
		clearSelection();
		load(search.value);
	},
);

/* -- Bulk tag editing -- */

const bulkModal = document.getElementById("bulk-modal");
const bulkTitle = document.getElementById("bulk-title");
const bulkAdd = document.getElementById("bulk-add");
const bulkRemove = document.getElementById("bulk-remove");

document.getElementById("sel-tag").addEventListener("click", () => {
	bulkTitle.textContent = `Edit tags for ${selectedIds.size} memes`;
	bulkAdd.value = "";
	bulkRemove.value = "";
	bulkModal.showModal();
});

wireDialog(bulkModal, { cancel: "bulk-cancel", submit: "bulk-save" });

document.getElementById("bulk-save").addEventListener("click", async () => {
	const add = bulkAdd.value
		.split(",")
		.map((t) => t.trim())
		.filter(Boolean);
	const remove = bulkRemove.value
		.split(",")
		.map((t) => t.trim())
		.filter(Boolean);
	if (!add.length && !remove.length) {
		bulkModal.close();
		return;
	}
	await Api.bulkTags([...selectedIds], add, remove);
	bulkModal.close();
	showAlert("Tags updated", "success");
	await load(search.value);
	restoreSelection();
});

/* -- Bulk auto-detect -- */

const selAutoBtn = document.getElementById("sel-auto");
if (!window.AI_ENABLED) selAutoBtn.style.display = "none";

selAutoBtn.addEventListener("click", () => {
	const autoModal = document.getElementById("auto-modal");
	const autoTitle = document.getElementById("auto-title");
	autoTitle.textContent = `Auto-detect for ${selectedIds.size} memes`;
	document.getElementById("auto-name").checked = true;
	document.getElementById("auto-desc").checked = true;
	document.getElementById("auto-tags").checked = true;
	registerAutoCallback(async (fields, startBtn) => {
		startBtn.classList.add("loading");
		const ids = [...selectedIds];
		const total = ids.length;
		let done = 0;
		const failed = [];
		const parallel = window.AI_PARALLEL || 3;
		autoTitle.textContent = `Processing 1/${total}...`;

		async function processOne(id) {
			done++;
			autoTitle.textContent = `Processing ${done}/${total}...`;
			const label =
				document.querySelector(`.card[data-id="${id}"]`)?.dataset.filename || id.slice(0, 8);
			try {
				let suggestion;
				try {
					suggestion = await Api.autoDetect(id);
				} catch (e) {
					failed.push(id);
					showAlert(`Detection failed for ${label}`, "error");
					return;
				}
				if (suggestion.error) {
					failed.push(id);
					showAlert(`Detection failed for ${label}: ${suggestion.error}`, "error");
					return;
				}
				const body = {};
				if (fields.includes("name") && suggestion.name) body.new_name = suggestion.name;
				if (fields.includes("description") && suggestion.description)
					body.description = suggestion.description;
				if (fields.includes("tags") && suggestion.tags) body.tags = suggestion.tags;
				if (Object.keys(body).length) {
					await Api.updateMeme(id, body);
				}
				showAlert(`Detected: ${suggestion.name || id.slice(0, 8)}`, "success");
			} catch (e) {
				failed.push(id);
				showAlert(`${suggestion?.name || id.slice(0, 8)}: ${e.message}`, "error");
			} finally {
				await load(search.value);
				restoreSelection();
			}
		}

		await runParallelQueue(ids, parallel, processOne);

		if (failed.length) {
			await Api.bulkTags(failed, ["auto-failed"], []);
			await load(search.value);
			restoreSelection();
			showAlert(`${total - failed.length} detected, ${failed.length} failed`, "warning");
		} else {
			showAlert(`Auto-detected ${total} meme${total > 1 ? "s" : ""}`, "success");
		}

		startBtn.classList.remove("loading");
		autoModal.close();
	});
	autoModal.showModal();
});
