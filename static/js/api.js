const Api = (() => {
	async function _json(url, method, body) {
		const opts = { method, headers: { "Content-Type": "application/json" } };
		if (body !== undefined) opts.body = JSON.stringify(body);
		const res = await fetch(url, opts);
		return res;
	}

	return {
		async listMemes(params) {
			const res = await fetch(`/api/memes?${params}`);
			return res.json();
		},

		async uploadFiles(formData) {
			const res = await fetch("/api/memes", { method: "POST", body: formData });
			return res.json();
		},

		async downloadUrl(url) {
			const res = await _json("/api/memes/url", "POST", { url });
			if (!res.ok) {
				const e = await res.json();
				throw new Error(e.error || "Download failed");
			}
			return res.json();
		},

		async updateMeme(uuid, body) {
			const res = await _json(`/api/memes/${encodeURIComponent(uuid)}`, "PUT", body);
			if (!res.ok) {
				const e = await res.json();
				throw new Error(e.error || "Error");
			}
			return res.json();
		},

		async deleteMeme(uuid) {
			return fetch(`/api/memes/${encodeURIComponent(uuid)}`, {
				method: "DELETE",
			});
		},

		async trackCopy(uuid) {
			const res = await fetch(`/api/memes/${encodeURIComponent(uuid)}/copy`, {
				method: "POST",
			});
			return res.json();
		},

		async autoDetect(uuid) {
			const res = await fetch(`/api/memes/${encodeURIComponent(uuid)}/auto`, {
				method: "POST",
			});
			if (!res.ok) {
				const e = await res.json();
				throw new Error(e.error || "Auto failed");
			}
			return res.json();
		},

		async bulkTags(uuids, add, remove) {
			const res = await _json("/api/memes/bulk/tags", "PUT", {
				uuids,
				add,
				remove,
			});
			return res.json();
		},
	};
})();
