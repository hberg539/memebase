/* -- State -- */

const selectedUuids = new Set();
const selectBar = document.getElementById("select-bar");
const selCount = document.getElementById("sel-count");

/* -- Selection management -- */

function updateSelectBar() {
	const n = selectedUuids.size;
	selCount.textContent = `${n} selected`;
	selectBar.classList.toggle("visible", n > 0);
}

function restoreSelection() {
	grid.querySelectorAll(".card").forEach((c) => {
		if (selectedUuids.has(c.dataset.uuid)) c.classList.add("selected");
	});
}

function clearSelection() {
	selectedUuids.clear();
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
		const u = card.dataset.uuid;
		if (selectedUuids.has(u)) {
			selectedUuids.delete(u);
			card.classList.remove("selected");
		} else {
			selectedUuids.add(u);
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
		selectedUuids.add(c.dataset.uuid);
		c.classList.add("selected");
	});
	updateSelectBar();
	resetSelDelete();
});

document.getElementById("sel-clear").addEventListener("click", clearSelection);

document.addEventListener("keydown", (e) => {
	if (e.key === "Escape" && selectedUuids.size && !modal.open) {
		clearSelection();
	}
});

/* -- Bulk delete -- */

const selDelBtn = document.getElementById("sel-delete");
let selDelConfirm = false;
selDelBtn.addEventListener("click", async () => {
	if (!selDelConfirm) {
		selDelConfirm = true;
		selDelBtn.textContent = `Delete ${selectedUuids.size}?`;
		selDelBtn.classList.add("confirm");
		return;
	}
	const count = selectedUuids.size;
	try {
		const promises = [...selectedUuids].map((u) => Api.deleteMeme(u));
		await Promise.all(promises);
		showAlert(`Deleted ${count} meme${count > 1 ? "s" : ""}`, "success");
		selectedUuids.forEach((u) => {
			const card = grid.querySelector(`.card[data-uuid="${u}"]`);
			if (card) card.classList.add("removing");
		});
		await new Promise((r) => setTimeout(r, 200));
	} catch (e) {
		showAlert(e.message || "Delete failed", "error");
	}
	selDelConfirm = false;
	selDelBtn.textContent = "Delete";
	selDelBtn.classList.remove("confirm");
	clearSelection();
	load(search.value);
});

function resetSelDelete() {
	selDelConfirm = false;
	selDelBtn.textContent = "Delete";
	selDelBtn.classList.remove("confirm");
}

/* -- Bulk tag editing -- */

const bulkModal = document.getElementById("bulk-modal");
const bulkTitle = document.getElementById("bulk-title");
const bulkAdd = document.getElementById("bulk-add");
const bulkRemove = document.getElementById("bulk-remove");

document.getElementById("sel-tag").addEventListener("click", () => {
	bulkTitle.textContent = `Edit tags for ${selectedUuids.size} memes`;
	bulkAdd.value = "";
	bulkRemove.value = "";
	bulkModal.showModal();
});

document.getElementById("bulk-cancel").addEventListener("click", () => bulkModal.close());
bulkModal.addEventListener("click", (e) => {
	if (e.target === bulkModal) bulkModal.close();
});

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
	await Api.bulkTags([...selectedUuids], add, remove);
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
	autoTitle.textContent = `Auto-detect for ${selectedUuids.size} memes`;
	document.getElementById("auto-name").checked = true;
	document.getElementById("auto-desc").checked = true;
	document.getElementById("auto-tags").checked = true;
	registerAutoCallback(async (fields, startBtn) => {
		startBtn.classList.add("loading");
		const uuids = [...selectedUuids];
		const total = uuids.length;
		let done = 0;
		const failed = [];
		const parallel = window.AI_PARALLEL || 3;
		autoTitle.textContent = `Processing 0/${total}...`;

		async function processOne(u) {
			try {
				let suggestion;
				try {
					suggestion = await Api.autoDetect(u);
				} catch (e) {
					failed.push(u);
					return;
				}
				if (suggestion.error) {
					failed.push(u);
					return;
				}
				const body = {};
				if (fields.includes("name") && suggestion.name) body.new_name = suggestion.name;
				if (fields.includes("description") && suggestion.description)
					body.description = suggestion.description;
				if (fields.includes("tags") && suggestion.tags) body.tags = suggestion.tags;
				if (Object.keys(body).length) {
					await Api.updateMeme(u, body);
				}
			} catch (e) {
				failed.push(u);
			}
			done++;
			autoTitle.textContent = `Processing ${done}/${total}...`;
			await load(search.value);
			restoreSelection();
		}

		await runParallelQueue(uuids, parallel, processOne);

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
