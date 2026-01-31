    # -- Proposal callback handlers -----------------------------------------

    @dp.callback_query(F.data.startswith("proposal_approve:"))
    async def handle_proposal_approve(callback: types.CallbackQuery):
        """Handle inline button click for approving proposal"""
        import httpx

        proposal_id = callback.data.split(":")[1]
        await callback.answer("Approving proposal...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://localhost:8700/api/proposals/{proposal_id}",
                    timeout=5.0
                )
                resp.raise_for_status()
                p = resp.json()

                resp = await client.post(
                    f"http://localhost:8700/api/proposals/{proposal_id}/apply",
                    timeout=30.0
                )
                resp.raise_for_status()
                result = resp.json()

            msg = f"✅ <b>Proposal approved and applied!</b>\n\n"
            msg += f"<b>{p['title']}</b>\n"
            msg += f"Modified {len(p['file_paths'])} file(s)"

            if result.get('commit_sha'):
                msg += f"\nCommit: <code>{result['commit_sha'][:8]}</code>"

            await callback.message.edit_text(msg, parse_mode=ParseMode.HTML)

        except Exception as e:
            await callback.message.answer(f"❌ Error approving proposal: {e}")

    @dp.callback_query(F.data.startswith("proposal_reject:"))
    async def handle_proposal_reject(callback: types.CallbackQuery):
        """Handle inline button click for rejecting proposal"""
        import httpx

        proposal_id = callback.data.split(":")[1]
        await callback.answer("Rejecting proposal...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"http://localhost:8700/api/proposals/{proposal_id}/reject",
                    json={"reason": "Rejected via Telegram button"},
                    timeout=5.0
                )
                resp.raise_for_status()

            await callback.message.edit_text(
                f"❌ <b>Proposal rejected</b>\n\n{callback.message.text}",
                parse_mode=ParseMode.HTML
            )

        except Exception as e:
            await callback.message.answer(f"❌ Error rejecting proposal: {e}")

    @dp.callback_query(F.data.startswith("proposal_info:"))
    async def handle_proposal_info(callback: types.CallbackQuery):
        """Handle inline button click for viewing proposal details"""
        import httpx
        from datetime import datetime

        proposal_id = callback.data.split(":")[1]
        await callback.answer("Fetching details...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://localhost:8700/api/proposals/{proposal_id}",
                    timeout=5.0
                )
                resp.raise_for_status()
                p = resp.json()

            lines = [
                f"<b>{p['title']}</b>",
                "",
                p['description'],
                "",
                f"<b>Files ({len(p['file_paths'])}):</b>",
            ]

            for fpath in p['file_paths']:
                lines.append(f"  • <code>{fpath}</code>")

            lines.extend([
                "",
                f"<b>Status:</b> {p['status']}",
                f"<b>Created:</b> {datetime.fromtimestamp(p['created_at']).strftime('%Y-%m-%d %H:%M')}",
            ])

            msg = "\n".join(lines)
            await callback.message.answer(msg, parse_mode=ParseMode.HTML)

        except Exception as e:
            await callback.message.answer(f"❌ Error fetching details: {e}")

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer(
            "/new — Start a fresh conversation\n"
            "/status — Show session info\n"
            "/session [name] [model] — Switch/create session\n"
            "/sessions — List all sessions\n"
            "/model [model] — Show/change model\n"
            "/task [title] — Create a task\n"
            "/task list [status] — List tasks\n"
            "/task done — Complete current task\n"
            "/task summary — Task counts\n"
            "/scratchpad — List notes\n"
            "/scratchpad <name> — Read a note\n"
            "/scratchpad <name> <text> — Write/append to a note\n"
            "/logs [hours] — Show log summary\n"
            "/cancel — Cancel current request\n"
            "/help — Show this message"
        )