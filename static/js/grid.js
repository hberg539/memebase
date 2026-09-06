/* -- State -- */

const grid = document.getElementById("grid");
const search = document.getElementById("search");
const sortSel = document.getElementById("sort");
const filtersEl = document.getElementById("filters");
const paginationEl = document.getElementById("pagination");

const clearBtn = document.getElementById("clear-all");

let allMemes = [];
let activeExtFilter = null;
const activeTagFilters = new Set();
let activeFavFilter = false;
let currentPage = 1;
let totalMemes = 0;
const SLIDING_PAGES = 5;

/* -- Per-page calculation -- */

let cachedPerPage = null;
function getPerPage() {
	if (cachedPerPage !== null) return cachedPerPage;
	const cfg = window.GRID_PER_PAGE;
	if (typeof cfg === "number" && cfg > 0) {
		cachedPerPage = cfg;
		return cachedPerPage;
	}
	const style = getComputedStyle(grid);
	const thumbSize =
		Number.parseInt(
			getComputedStyle(document.documentElement).getPropertyValue("--thumb-size"),
			10,
		) || 220;
	const gap = Number.parseFloat(style.columnGap) || 16;
	const contentWidth =
		grid.clientWidth - Number.parseFloat(style.paddingLeft) - Number.parseFloat(style.paddingRight);
	const cols = Math.max(1, Math.floor((contentWidth + gap) / (thumbSize + gap)));
	const gridTop = grid.getBoundingClientRect().top;
	const availableHeight = window.innerHeight - gridTop;
	const rows = Math.max(1, Math.ceil((availableHeight + gap) / (thumbSize + gap)));
	cachedPerPage = cols * rows;
	return cachedPerPage;
}

/* -- Card template -- */

function buildCardHtml(m, isNew) {
	const src = `/memes/${m.id}/${encodeURIComponent(m.filename)}`;
	const ext = m.ext;
	const thumbEnabled = window.THUMBNAILS_ENABLED;
	const skipTypes = window.THUMBNAILS_SKIP_TYPES || [];
	const useThumb = thumbEnabled && !skipTypes.includes(ext);
	let media;
	if (useThumb) {
		const thumbExt = window.THUMBNAILS_FORMAT === "jpeg" ? "jpg" : "webp";
		media = `<img src="/thumbnails/${m.id}.${thumbExt}" alt="${esc(m.filename)}" loading="lazy">`;
	} else if (isVideo(m.filename)) {
		media = `<video src="${src}" muted loop preload="metadata"></video>`;
	} else {
		media = `<img src="${src}" alt="${esc(m.filename)}" loading="lazy">`;
	}
	const tags = m.tags.length
		? `<div class="card-tags">${m.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</div>`
		: "";
	return `
    <div class="card${isNew ? " card-new" : ""}" data-id="${esc(m.id)}" data-filename="${esc(m.filename)}" data-desc="${esc(m.description)}" data-tags="${esc(m.tags.join(","))}" data-created="${esc(m.created_at || "")}" data-fav="${m.favorite || 0}" data-size="${m.size || 0}">
      <button class="btn-fav${m.favorite ? " active" : ""}" title="Favorite">${icon(m.favorite ? "heart" : "heart", 18)}</button>
      <button class="btn-copy" data-src="${src}" data-filename="${esc(m.filename)}">${icon(canCopy(m.filename) ? "clipboard" : "download", 18)}</button>
      ${media}
      <div class="card-overlay">
        ${tags}
        <div class="card-name">${(() => {
					const d = m.filename.lastIndexOf(".");
					return d > 0
						? `<span class="name-base">${esc(m.filename.slice(0, d))}</span>${esc(m.filename.slice(d))}`
						: esc(m.filename);
				})()}</div>
      </div>
    </div>`;
}

/* -- Clear button state -- */

function updateClearBtn() {
	const active = search.value || activeExtFilter || activeTagFilters.size || activeFavFilter;
	clearBtn.disabled = !active;
}

/* -- Data loading -- */

async function load(q = "") {
	const params = new URLSearchParams();
	if (q) params.set("q", q);
	params.set("sort", sortSel.value);
	params.set("page", currentPage);
	params.set("per_page", getPerPage());
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
	updateClearBtn();
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
		html += `<span class="filter-chip ext-filter${active}" data-ext="${esc(ext)}">${esc(ext)} (${count})</span>`;
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

let prevIds = new Set();
function renderGrid() {
	const memes = allMemes;
	if (!memes.length) {
		prevIds = new Set();
		grid.innerHTML = '<div class="grid-empty">No memes found</div>';
		return;
	}
	const newIds = new Set(memes.map((m) => m.id));
	grid.innerHTML = memes.map((m) => buildCardHtml(m, !prevIds.has(m.id) && prevIds.size)).join("");
	prevIds = newIds;
}

/* -- Pagination -- */

function renderPagination() {
	const pageSize = getPerPage();
	const totalPages = Math.max(1, Math.ceil(totalMemes / pageSize));

	const pages = [];
	if (totalPages <= SLIDING_PAGES + 3) {
		for (let i = 1; i <= totalPages; i++) pages.push(i);
	} else {
		const half = Math.floor(SLIDING_PAGES / 2);
		let start = Math.max(2, currentPage - half);
		let end = start + SLIDING_PAGES - 1;
		if (end > totalPages - 1) {
			end = totalPages - 1;
			start = end - SLIDING_PAGES + 1;
		}
		pages.push(1);
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

grid.addEventListener(
	"mouseenter",
	(e) => {
		const vid = e.target.closest(".card video");
		if (vid) vid.play().catch(() => {});
	},
	true,
);
grid.addEventListener(
	"mouseleave",
	(e) => {
		const vid = e.target.closest(".card video");
		if (vid) vid.pause();
	},
	true,
);

paginationEl.addEventListener("click", async (e) => {
	const btn = e.target.closest(".page-btn");
	if (!btn || btn.disabled) return;
	currentPage = Number.parseInt(btn.dataset.page, 10);
	prevIds = new Set();
	window.scrollTo({ top: 0 });
	await load(search.value);
});

let timer;
const triggerSearch = () => {
	clearTimeout(timer);
	activeExtFilter = null;
	activeTagFilters.clear();
	activeFavFilter = false;
	currentPage = 1;
	prevIds = new Set();
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
	prevIds = new Set();
	load(search.value);
});

function resetView() {
	search.value = "";
	sortSel.value = "newest";
	activeExtFilter = null;
	activeTagFilters.clear();
	activeFavFilter = false;
	currentPage = 1;
	prevIds = new Set();
	clearSelection();
	load();
}

clearBtn.addEventListener("click", resetView);
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
	prevIds = new Set();
	load(search.value);
});
