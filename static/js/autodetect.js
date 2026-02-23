/* -- Shared auto-detect modal -- */

let _autoCallback = null;

function registerAutoCallback(fn) {
	_autoCallback = fn;
}

function runParallelQueue(items, concurrency, processOne) {
	const queue = items.slice();
	async function worker() {
		while (queue.length) {
			const item = queue.shift();
			await processOne(item);
		}
	}
	return Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, () => worker()));
}

/* -- Auto-modal button wiring -- */
{
	const autoModal = document.getElementById("auto-modal");
	wireDialog(autoModal, { cancel: "auto-cancel", submit: "auto-start" });
	document.getElementById("auto-start").addEventListener("click", () => {
		const fields = [];
		if (document.getElementById("auto-name").checked) fields.push("name");
		if (document.getElementById("auto-desc").checked) fields.push("description");
		if (document.getElementById("auto-tags").checked) fields.push("tags");
		if (!fields.length) {
			autoModal.close();
			return;
		}
		const startBtn = document.getElementById("auto-start");
		if (_autoCallback) _autoCallback(fields, startBtn);
	});
}
