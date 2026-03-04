/* -- DOM refs -- */

const modal = document.getElementById("modal");
const mMedia = document.getElementById("m-media");
const mName = document.getElementById("m-name");
const mExt = document.getElementById("m-ext");
const mTags = document.getElementById("m-tags");
const mDesc = document.getElementById("m-desc");
const mDate = document.getElementById("m-date");
let currentId = null;

const autoOpenBtn = document.getElementById("m-auto-open");
if (!window.AI_ENABLED) autoOpenBtn.style.display = "none";
const delBtn = document.getElementById("m-delete");

/* -- Open modal (card click) -- */

grid.addEventListener("click", (e) => {
	const favBtn = e.target.closest(".btn-fav");
	if (favBtn) {
		e.stopPropagation();
		const card = favBtn.closest(".card");
		const newFav = card.dataset.fav === "1" ? 0 : 1;
		card.dataset.fav = newFav;
		favBtn.innerHTML = icon("heart", 18);
		favBtn.classList.toggle("active", !!newFav);
		refreshIcons();
		Api.updateMeme(card.dataset.id, { favorite: newFav });
		return;
	}
	const copyBtn = e.target.closest(".btn-copy");
	if (copyBtn) {
		e.stopPropagation();
		const card = copyBtn.closest(".card");
		if (canCopy(copyBtn.dataset.filename)) copyImage(copyBtn.dataset.src, copyBtn);
		else downloadFile(copyBtn.dataset.src, copyBtn.dataset.filename);
		return;
	}
	const card = e.target.closest(".card");
	if (!card) return;
	currentId = card.dataset.id;
	const filename = card.dataset.filename;
	const [stem, ext] = splitExt(filename);
	const src = `/memes/${currentId}/${encodeURIComponent(filename)}`;
	if (isVideo(filename)) {
		mMedia.innerHTML = `<video src="${src}" controls loop autoplay></video>`;
	} else {
		mMedia.innerHTML = `<img src="${src}" alt="">`;
	}
	mName.value = stem;
	mExt.textContent = ext;
	mTags.value = card.dataset.tags;
	mDesc.value = card.dataset.desc;
	const mFav = document.getElementById("m-fav");
	const isFav = card.dataset.fav === "1";
	mFav.innerHTML = `${icon("heart", 14)} Favorite`;
	mFav.classList.toggle("active", isFav);
	mDate.textContent = card.dataset.created ? card.dataset.created.replace("T", " ") : "";
	document.getElementById("m-size").textContent = formatSize(Number(card.dataset.size) || 0);
	const mCopy = document.getElementById("m-copy");
	mCopy.innerHTML =
		icon(canCopy(filename) ? "clipboard" : "download", 14) +
		(canCopy(filename) ? " Copy" : " Download");
	autoOpenBtn.disabled = isVideo(filename);
	autoOpenBtn.title = isVideo(filename) ? "Auto-detect is not available for videos" : "";
	modal.showModal();
	modal.focus();
	refreshIcons();
});

/* -- Favorite -- */

document.getElementById("m-fav").addEventListener("click", async () => {
	const mFav = document.getElementById("m-fav");
	const card = grid.querySelector(`.card[data-id="${currentId}"]`);
	const newFav = card && card.dataset.fav === "1" ? 0 : 1;
	if (card) {
		card.dataset.fav = newFav;
		const btn = card.querySelector(".btn-fav");
		if (btn) {
			btn.innerHTML = icon("heart", 18);
			btn.classList.toggle("active", !!newFav);
		}
	}
	mFav.innerHTML = `${icon("heart", 14)} Favorite`;
	mFav.classList.toggle("active", !!newFav);
	refreshIcons();
	await Api.updateMeme(currentId, { favorite: newFav });
});

/* -- Copy / Download -- */

document.getElementById("m-copy").addEventListener("click", () => {
	const mCopy = document.getElementById("m-copy");
	const filename = mName.value.trim() + mExt.textContent;
	const mediaSrc = mMedia.querySelector("img, video")?.src || "";
	if (canCopy(filename)) copyImage(mediaSrc, mCopy);
	else downloadFile(mediaSrc, filename);
});

/* -- Delete -- */

const resetDel = confirmButton(delBtn, "Really delete?", async () => {
	try {
		await Api.deleteMeme(currentId);
		modal.close();
		showAlert(`Deleted ${mName.value}${mExt.textContent}`, "success");
		const card = grid.querySelector(`.card[data-id="${currentId}"]`);
		if (card) {
			card.classList.add("removing");
			await new Promise((r) => setTimeout(r, 200));
		}
		load(search.value);
	} catch (e) {
		showAlert(`${mName.value}${mExt.textContent}: ${e.message || "Delete failed"}`, "error");
	}
});

/* -- Auto-detect -- */

autoOpenBtn.addEventListener("click", () => {
	const autoModal = document.getElementById("auto-modal");
	document.getElementById("auto-title").textContent = "Auto-detect";
	document.getElementById("auto-name").checked = true;
	document.getElementById("auto-desc").checked = true;
	document.getElementById("auto-tags").checked = true;
	registerAutoCallback(async (fields, startBtn) => {
		startBtn.classList.add("loading");
		try {
			const data = await Api.autoDetect(currentId);
			if (fields.includes("name") && data.name) mName.value = data.name;
			if (fields.includes("description") && data.description) mDesc.value = data.description;
			if (fields.includes("tags") && data.tags) mTags.value = data.tags.join(", ");
		} catch (e) {
			showAlert(`${mName.value}${mExt.textContent}: Auto failed - ${e.message}`, "error");
		} finally {
			startBtn.classList.remove("loading");
			autoModal.close();
		}
	});
	autoModal.showModal();
});

/* -- Close & keyboard -- */

modal.addEventListener("close", () => {
	resetDel();
	const vid = mMedia.querySelector("video");
	if (vid) {
		vid.pause();
		vid.src = "";
	}
});

wireDialog(modal, { cancel: "m-cancel", submit: "m-save" });
modal.addEventListener("keydown", (e) => {
	if (e.key === "f" && !e.target.matches("input, textarea")) {
		e.preventDefault();
		document.getElementById("m-fav").click();
	}
});

/* -- Save -- */

document.getElementById("m-save").addEventListener("click", async () => {
	const body = {};
	body.new_name = mName.value.trim();
	body.description = mDesc.value;
	body.tags = mTags.value
		.split(",")
		.map((t) => t.trim())
		.filter(Boolean);
	try {
		await Api.updateMeme(currentId, body);
	} catch (e) {
		showAlert(`${mName.value}${mExt.textContent}: ${e.message}`, "error");
		return;
	}
	modal.close();
	showAlert(`Saved ${mName.value}${mExt.textContent}`, "success");
	load(search.value);
});
