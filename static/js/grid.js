/* -- State -- */

const grid = document.getElementById("grid");
const search = document.getElementById("search");
const sortSel = document.getElementById("sort");
const filtersEl = document.getElementById("filters");
const paginationEl = document.getElementById("pagination");

let allMemes = [];
let activeExtFilter = null;
const activeTagFilters = new Set();
let activeFavFilter = false;
let currentPage = 1;
let totalMemes = 0;

/* -- Card template -- */

function buildCardHtml(m, isNew) {
	const src = `/memes/${m.uuid}/${encodeURIComponent(m.filename)}`;
	const media = isVideo(m.filename)
		? `<video src="${src}" muted loop preload="metadata" onmouseenter="this.play()" onmouseleave="this.pause()"></video>`
		: `<img src="${src}" alt="${esc(m.filename)}" loading="lazy">`;
	const tags = m.tags.length
		? `<div class="card-tags">${m.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</div>`
		: "";
	return `
    <div class="card${isNew ? " card-new" : ""}" data-uuid="${esc(m.uuid)}" data-filename="${esc(m.filename)}" data-desc="${esc(m.description)}" data-tags="${esc(m.tags.join(","))}" data-created="${esc(m.created_at || "")}" data-copies="${m.copy_count || 0}" data-fav="${m.favorite || 0}" data-size="${m.size || 0}">
      <button class="btn-fav${m.favorite ? " active" : ""}" title="Favorite">${icon(m.favorite ? "heart" : "heart", 18)}</button>
      <button class="btn-copy" data-src="${src}" data-filename="${esc(m.filename)}">${icon(canCopy(m.filename) ? "clipboard" : "download", 18)}</button>
      ${media}
      <div class="name">${(() => {
				const d = m.filename.lastIndexOf(".");
				return d > 0
					? `<span class="name-base">${esc(m.filename.slice(0, d))}</span>${esc(m.filename.slice(d))}`
					: esc(m.filename);
			})()}</div>
      ${tags}
    </div>`;
}

/* -- Data loading -- */

async function load(q = "") {
	const params = new URLSearchParams();
	if (q) params.set("q", q);
	params.set("sort", sortSel.value);
	params.set("page", currentPage);
	if (activeExtFilter) params.set("ext", activeExtFilter);
	for (const t of activeTagFilters) params.append("tag", t);
	if (activeFavFilter) params.set("fav", "1");
	const data = await Api.listMemes(params);
	allMemes = data.memes;
	totalMemes = data.total;
	buildFilters(data.filters);
	renderGrid();
	renderPagination();
	refreshIcons();
}

/* -- Filters -- */

function buildFilters(filters) {
	let html = "";
	const active_fav = activeFavFilter ? " active" : "";
	html += `<span class="filter-chip fav-filter${active_fav}" data-fav="1">${icon("heart", 12)} Favorites (${filters.fav_count})</span>`;
	html += '<span class="filter-sep"></span>';
	for (const [ext, count] of Object.entries(filters.exts).sort((a, b) =>
		a[0].localeCompare(b[0]),
	)) {
		const active = activeExtFilter === ext ? " active" : "";
		html += `<span class="filter-chip ext${active}" data-ext="${esc(ext)}">${esc(ext)} (${count})</span>`;
	}
	if (Object.keys(filters.tags).length) {
		html += '<span class="filter-sep"></span>';
		for (const [tag, count] of Object.entries(filters.tags).sort((a, b) =>
			a[0].localeCompare(b[0]),
		)) {
			const active = activeTagFilters.has(tag) ? " active" : "";
			html += `<span class="filter-chip tag-filter${active}" data-tag="${esc(tag)}">${esc(tag)} (${count})</span>`;
		}
	}
	filtersEl.innerHTML = html;
}

/* -- Grid rendering -- */

let prevUuids = new Set();
function renderGrid() {
	const memes = allMemes;
	if (!memes.length) {
		prevUuids = new Set();
		grid.innerHTML = '<div class="empty">No memes found</div>';
		return;
	}
	const newUuids = new Set(memes.map((m) => m.uuid));
	grid.innerHTML = memes
		.map((m) => buildCardHtml(m, !prevUuids.has(m.uuid) && prevUuids.size))
		.join("");
	prevUuids = newUuids;
}

/* -- Pagination -- */

function renderPagination() {
	const pageSize = window.GRID_PAGE_SIZE || 50;
	const totalPages = Math.max(1, Math.ceil(totalMemes / pageSize));

	const maxVisible = 7;
	const pages = [];
	if (totalPages <= maxVisible) {
		for (let i = 1; i <= totalPages; i++) pages.push(i);
	} else {
		pages.push(1);
		let start = Math.max(2, currentPage - 1);
		let end = Math.min(totalPages - 1, currentPage + 1);
		if (currentPage <= 3) {
			start = 2;
			end = 4;
		}
		if (currentPage >= totalPages - 2) {
			start = totalPages - 3;
			end = totalPages - 1;
		}
		if (start > 2) pages.push("...");
		for (let i = start; i <= end; i++) pages.push(i);
		if (end < totalPages - 1) pages.push("...");
		pages.push(totalPages);
	}

	let html = '<div class="pagination">';
	html += `<button class="page-btn" data-page="${currentPage - 1}" ${currentPage === 1 ? "disabled" : ""}>${icon("chevron-left", 16)}</button>`;
	for (const p of pages) {
		if (p === "...") {
			html += '<span class="page-ellipsis">...</span>';
		} else {
			html += `<button class="page-btn${p === currentPage ? " active" : ""}" data-page="${p}">${p}</button>`;
		}
	}
	html += `<button class="page-btn" data-page="${currentPage + 1}" ${currentPage === totalPages ? "disabled" : ""}>${icon("chevron-right", 16)}</button>`;
	html += `<span class="page-info">${totalMemes} memes</span>`;
	html += "</div>";
	paginationEl.innerHTML = html;
	refreshIcons();
}

/* -- Event listeners -- */

paginationEl.addEventListener("click", (e) => {
	const btn = e.target.closest(".page-btn");
	if (!btn || btn.disabled) return;
	currentPage = Number.parseInt(btn.dataset.page);
	prevUuids = new Set();
	load(search.value);
	window.scrollTo({ top: 0, behavior: "smooth" });
});

let timer;
const triggerSearch = () => {
	clearTimeout(timer);
	activeExtFilter = null;
	activeTagFilters.clear();
	activeFavFilter = false;
	currentPage = 1;
	prevUuids = new Set();
	load(search.value);
};
search.addEventListener("input", () => {
	clearTimeout(timer);
	timer = setTimeout(triggerSearch, 300);
});
search.addEventListener("keydown", (e) => {
	if (e.key === "Enter") triggerSearch();
});
sortSel.addEventListener("change", () => {
	currentPage = 1;
	prevUuids = new Set();
	load(search.value);
});

function resetView() {
	search.value = "";
	sortSel.value = "newest";
	activeExtFilter = null;
	activeTagFilters.clear();
	activeFavFilter = false;
	currentPage = 1;
	prevUuids = new Set();
	clearSelection();
	load();
}

document.getElementById("clear-all").addEventListener("click", resetView);
document.getElementById("logo").addEventListener("click", resetView);

filtersEl.addEventListener("click", (e) => {
	const chip = e.target.closest(".filter-chip");
	if (!chip) return;
	if (chip.dataset.fav !== undefined) {
		activeFavFilter = !activeFavFilter;
	} else if (chip.dataset.ext !== undefined) {
		activeExtFilter = activeExtFilter === chip.dataset.ext ? null : chip.dataset.ext;
	} else if (chip.dataset.tag !== undefined) {
		const tag = chip.dataset.tag;
		if (activeTagFilters.has(tag)) activeTagFilters.delete(tag);
		else activeTagFilters.add(tag);
	}
	currentPage = 1;
	prevUuids = new Set();
	load(search.value);
});
