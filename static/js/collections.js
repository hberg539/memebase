/* -- Collection state -- */

let activeCollection = "";
let allCollections = [];

function getActiveCollection() {
	return activeCollection || null;
}

/* -- DOM refs -- */

const collSelect = document.getElementById("collection-select");
const collManageBtn = document.getElementById("btn-coll-manage");
const collModal = document.getElementById("coll-modal");
const collList = document.getElementById("coll-list");
const collNewName = document.getElementById("coll-new-name");
const collAddBtn = document.getElementById("coll-add-btn");

/* -- Dropdown -- */

function populateDropdown() {
	let html = '<option value="">No collection</option>';
	for (const c of allCollections) {
		const sel = c.slug === activeCollection ? " selected" : "";
		html += `<option value="${esc(c.slug)}"${sel}>${esc(c.name)}</option>`;
	}
	collSelect.innerHTML = html;
}

function syncCollectionToUrl() {
	const url = new URL(window.location);
	if (activeCollection) {
		url.searchParams.set("collection", activeCollection);
	} else {
		url.searchParams.delete("collection");
	}
	history.replaceState(null, "", url);
}

collSelect.addEventListener("change", () => {
	activeCollection = collSelect.value;
	syncCollectionToUrl();
	activeExtFilter = null;
	activeTagFilters.clear();
	activeFavFilter = false;
	currentPage = 1;
	prevIds = new Set();
	clearSelection();
	load(search.value);
});

/* -- Manage dialog -- */

collManageBtn.addEventListener("click", async () => {
	await refreshCollections();
	renderCollList();
	collModal.showModal();
	collModal.focus();
});

wireDialog(collModal, { cancel: "coll-close" });

function renderCollList() {
	if (!allCollections.length) {
		collList.innerHTML = '<div class="coll-empty">No collections yet</div>';
		return;
	}
	let html = "";
	for (const c of allCollections) {
		html += `<div class="coll-row" data-slug="${esc(c.slug)}">
			<span class="coll-name">${esc(c.name)}</span>
			<button class="btn-coll-rename btn-meta" data-slug="${esc(c.slug)}">Rename</button>
			<button class="btn-coll-delete btn-meta" data-slug="${esc(c.slug)}">Delete</button>
		</div>`;
	}
	collList.innerHTML = html;
}

/* -- Add collection -- */

collAddBtn.addEventListener("click", async () => {
	const name = collNewName.value.trim();
	if (!name) return;
	try {
		await Api.createCollection(name);
		collNewName.value = "";
		await refreshCollections();
		renderCollList();
		populateDropdown();
	} catch (e) {
		showAlert(e.message, "error");
	}
});

collNewName.addEventListener("keydown", (e) => {
	if (e.key === "Enter") collAddBtn.click();
});

/* -- Rename / Delete -- */

collList.addEventListener("click", async (e) => {
	const renameBtn = e.target.closest(".btn-coll-rename");
	if (renameBtn) {
		const slug = renameBtn.dataset.slug;
		const current = allCollections.find((c) => c.slug === slug);
		const newName = prompt("New name:", current?.name || "");
		if (!newName?.trim()) return;
		try {
			const updated = await Api.renameCollection(slug, newName.trim());
			if (activeCollection === slug) {
				activeCollection = updated.slug;
				syncCollectionToUrl();
			}
			await refreshCollections();
			renderCollList();
			populateDropdown();
			// Cards carry the collection slug, so reload the grid to pick up the new one.
			load(search.value);
		} catch (err) {
			showAlert(err.message, "error");
		}
		return;
	}
	const deleteBtn = e.target.closest(".btn-coll-delete");
	if (deleteBtn) {
		const slug = deleteBtn.dataset.slug;
		if (!confirm("Delete this collection? Memes must be moved out first.")) return;
		try {
			await Api.deleteCollection(slug);
			if (activeCollection === slug) {
				activeCollection = "";
				syncCollectionToUrl();
			}
			await refreshCollections();
			renderCollList();
			populateDropdown();
			load(search.value);
		} catch (err) {
			showAlert(err.message, "error");
		}
	}
});

/* -- Load collections -- */

async function refreshCollections() {
	allCollections = await Api.listCollections();
}

async function loadCollections() {
	// The grid only needs the active slug, so start loading it right away
	// instead of waiting on the collections request.
	activeCollection = new URLSearchParams(window.location.search).get("collection") || "";
	const gridLoad = load();
	try {
		await refreshCollections();
	} catch (err) {
		showAlert(err.message, "error");
		populateDropdown();
		return;
	}
	if (activeCollection && !allCollections.some((c) => c.slug === activeCollection)) {
		// Stale or bogus slug in the URL: fall back to the unfiled view.
		activeCollection = "";
		syncCollectionToUrl();
		await gridLoad;
		load();
	}
	populateDropdown();
}

/* -- Init -- */

loadCollections();
