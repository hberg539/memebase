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
			if (!res.ok) {
				let msg = "Upload failed";
				try {
					const e = await res.json();
					msg = e.error || msg;
				} catch {}
				throw new Error(msg);
			}
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

		async updateMeme(id, body) {
			const res = await _json(`/api/memes/${encodeURIComponent(id)}`, "PUT", body);
			if (!res.ok) {
				const e = await res.json();
				throw new Error(e.error || "Error");
			}
			return res.json();
		},

		async deleteMeme(id) {
			return fetch(`/api/memes/${encodeURIComponent(id)}`, {
				method: "DELETE",
			});
		},

		async autoDetect(id) {
			const res = await fetch(`/api/memes/${encodeURIComponent(id)}/auto`, {
				method: "POST",
			});
			if (!res.ok) {
				const e = await res.json();
				throw new Error(e.error || "Auto failed");
			}
			return res.json();
		},

		async bulkTags(ids, add, remove) {
			const res = await _json("/api/memes/bulk/tags", "PUT", {
				ids,
				add,
				remove,
			});
			return res.json();
		},
	};
})();
