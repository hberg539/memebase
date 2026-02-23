/* -- Dialog utilities -- */

function wireDialog(dialog, opts) {
	dialog.addEventListener("click", (e) => {
		if (e.target === dialog) dialog.close();
	});
	if (opts.cancel) {
		document.getElementById(opts.cancel).addEventListener("click", () => dialog.close());
	}
	if (opts.submit) {
		dialog.addEventListener("keydown", (e) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				document.getElementById(opts.submit).click();
			}
		});
	}
}

function confirmButton(btn, confirmLabel, onConfirm) {
	let armed = false;
	const label = btn.textContent;
	const reset = () => {
		armed = false;
		btn.textContent = label;
		btn.classList.remove("confirm");
	};
	btn.addEventListener("click", async () => {
		if (!armed) {
			armed = true;
			btn.textContent = typeof confirmLabel === "function" ? confirmLabel() : confirmLabel;
			btn.classList.add("confirm");
			return;
		}
		await onConfirm();
		reset();
	});
	return reset;
}

function anyDialogOpen() {
	return !!document.querySelector("dialog[open]");
}

/* -- Dialog close animation -- */

document.querySelectorAll("dialog").forEach((d) => {
	const origClose = d.close.bind(d);
	d.close = () => {
		if (!d.open) return;
		d.classList.add("closing");
		d.addEventListener(
			"transitionend",
			() => {
				d.classList.remove("closing");
				origClose();
			},
			{ once: true },
		);
		setTimeout(() => {
			d.classList.remove("closing");
			origClose();
		}, 200);
	};
});
