"""Generate the deterministic Meera Sethi six-month development corpus."""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "fixtures" / "development-500.json"
GT = ROOT / "GROUND_TRUTH.json"
RNG = random.Random(260630)
IST = timezone(timedelta(hours=5, minutes=30))

records: list[dict] = []
labels: dict[str, list[str]] = defaultdict(list)


def add(day: str, hm: str, raw: str, formatted: str, application: str,
        channel: str | None = None, *plant_labels: str) -> None:
    stamp = datetime.combine(date.fromisoformat(day), time.fromisoformat(hm), IST).isoformat()
    rid = f"meera_{day}_{len(records)+1:04d}"
    metadata = {"source": "dictation", "application": application, "language": "en-IN"}
    if channel:
        metadata["channel"] = channel
    records.append({"transcript_id": rid, "raw_asr": raw, "formatted_text": formatted,
                    "occurred_at": stamp, "metadata": metadata})
    for label in plant_labels:
        labels[label].append(rid)


def planted() -> None:
    p = add
    p("2026-01-05","09:41","okay intro note im meera sethi product lead at turnery studio joined fourteenth august twenty twenty three","I’m Meera Sethi, Product Lead at Ternary Studio. I joined on 14 August 2023.","notion",None,"identity_role","join_date")
    p("2026-01-05","10:18","morning quick atlus one aaron owns back end sophia owns design and prea is our acne contact","Morning—quick Atlas one. Arun owns backend, Sofia owns design, and Priya is our Acme contact.","slack","#atlas-delivery","atlas_owners","contact_old","slack_opening","assignment_style")
    p("2026-01-06","20:48","atlus review six january prea aaron sophia me decision stay tuesdays three g m t action aaron invoice states by friday","Atlas review, 6 January. Attendees: Priya, Arun, Sofia, Meera. Decision: keep the review on Tuesdays at 15:00 GMT. Action: Arun to confirm invoice states by Friday.","zoom","Atlas client review","review_slot_old","recap_order","assignment_style")
    p("2026-01-08","11:12","hi prea thanks for the review we folded in navigation change new paragraph can you confirm invoice labels by noon tuesday best meera","Hi Priya,\n\nThanks for the review. We have incorporated the navigation change.\n\nCould you confirm the invoice labels by noon Tuesday?\n\nBest,\nMeera","outlook","client-email","email_prose","email_signoff","assignment_style")
    p("2026-01-12","14:37","meter line discovery starts today it tests replacing stripe building with a custom usage led invoice service","Meterline discovery starts on 12 January. It tests replacing Stripe Billing with a custom usage-led invoicing service.","notion","Meterline","meterline_purpose")
    p("2026-01-14","15:22","heading context colon fleet admins need vehicle status driver access invoices and support in one responsive portal","Context\n\nAtlas will replace Acme’s legacy fleet-manager portal with a responsive portal covering vehicle status, driver access, invoices, and support.","notion","Atlas brief","atlas_scope_part1","decision_format")
    p("2026-01-19","09:52","morning quick cedar one omar send the archive index by thursday","Morning—quick Cedar one. Omar, please send the archive index by Thursday.","slack","#product-strategy","slack_opening","assignment_style")
    p("2026-01-22","16:08","cedar is the north wind analytics hand off im the outgoing product lead","Cedar is the Northwind analytics handoff. I’m the outgoing product lead.","notion","Cedar","cedar_fact")
    p("2026-01-29","17:44","cedar final walk through today dashboard prototype and research archive transferred access check monday","Cedar final walkthrough, 29 January. The dashboard prototype and research archive were transferred. Access check: Monday.","zoom","Cedar handoff","cedar_episode")
    p("2026-02-02","10:06","north wind confirmed access cedar can be archived","Northwind confirmed access on 2 February. Cedar can be archived.","slack","#product-strategy","cedar_complete")
    p("2026-02-04","14:18","heading context colon custom billing may reduce manual exports heading decision colon working direction build meter line in q two heading rationale colon control usage invoice rules heading open questions colon reconciliation effort","Context\n\nCustom billing may reduce manual exports.\n\nDecision\n\nThe working direction is to build Meterline in Q2.\n\nRationale\n\nA custom service could give Acme control of usage invoice rules.\n\nOpen questions\n\nReconciliation effort remains untested.","notion","Meterline decision","meterline_old","decision_format")
    p("2026-02-12","20:51","atlus review twelfth feb prea aaron sophia me decision move recurring review to thursday at three g m t action aaron invoice export check for nineteenth","Atlas review, 12 February. Attendees: Priya, Arun, Sofia, Meera. Decision: move the recurring review to Thursdays at 15:00 GMT. Action: Arun owns the invoice export check for 19 February.","zoom","Atlas client review","review_slot_new","review_slot_old","recap_order","assignment_style")
    p("2026-02-16","09:43","morning quick atlus one sophia share the responsive nav pass by thursday","Morning—quick Atlas one. Sofia, share the responsive navigation pass by Thursday.","slack","#atlas-delivery","slack_opening","assignment_style")
    p("2026-02-19","20:57","atlus review nineteen feb decision invoice export empty state stays inline action aaron update by monday unresolved vat label","Atlas review, 19 February. Decision: the invoice-export empty state stays inline. Action: Arun to update it by Monday. Unresolved: VAT label.","zoom","Atlas client review","episode_review_0219","recap_order")
    p("2026-03-02","09:38","morning quick atlus one aaron has release sign off now please post the back end risk list by wednesday","Morning—quick Atlas one. Arun now has release sign-off. Please post the backend risk list by Wednesday.","slack","#atlas-delivery","arun_lead_implied","assignment_style","slack_opening")
    p("2026-03-05","20:46","atlus review five march decision beta keeps invoice pdf action our tech lead aaron to close timeout issue by monday","Atlas review, 5 March. Decision: beta keeps invoice PDF. Action: our technical lead, Arun, to close the timeout issue by Monday.","zoom","Atlas client review","arun_lead_implied","episode_review_0305","recap_order")
    p("2026-03-10","11:07","confirming title aaron menon is atlas technical lead from second march not varun varun is acne security","Confirming the title: Arun Menon has been Atlas Technical Lead since 2 March. He is not Varun Menon; Varun is Acme’s security engineer.","slack","#atlas-delivery","arun_lead_current","people_disambiguation")
    p("2026-03-13","16:21","nandinee is my manager through sunday lina joins monday and takes my one to ones","Nandini Rao is my manager through Sunday. Leena Iyer joins on Monday and will take over my one-to-ones.","notion","private-work-note","manager_old","manager_new")
    p("2026-03-16","10:14","internal intro lina iyer starts today as director of product she is my manager now nandinee remains atlus sponsor","Leena Iyer starts today as Director of Product. She is my manager now; Nandini remains Atlas sponsor.","slack","#product-strategy","manager_old","manager_new")
    p("2026-03-23","14:11","harbour proposal reduce steps for fleet admin to invite verify and first login a driver not training or payroll","Harbor proposal: reduce the steps for a fleet administrator to invite and verify a driver and complete first login. It does not cover training or payroll.","notion","Harbor brief","harbor_scope")
    p("2026-04-06","09:47","morning quick harbour one formal start today omar runs research logistics sophia interaction design pilot is eight june","Morning—quick Harbor one. The project formally starts today. Omar runs research logistics, Sofia owns interaction design, and the pilot is 8 June.","slack","#harbor-pilot","harbor_owners","harbor_date_old","slack_opening")
    p("2026-04-06","13:36","open figma acne product slash atlus the driver invite flow is there","Open the Figma project `Acme Product / Atlas`; the driver-invite flow is there.","figma","Acme Product / Atlas","figma_new")
    p("2026-04-07","10:03","use the frame in figma acne product slash atlus not the old comments link","Use the frame in Figma project `Acme Product / Atlas`, not the old comments link.","slack","#design-review","figma_new")
    p("2026-04-09","15:06","heading context stripe building handles current invoices heading decision keep stripe billing for twenty twenty six and build thin export service stop meter line heading rationale custom service does not cut reconciliation enough heading open questions export schema owner","Context\n\nStripe Billing handles current invoices.\n\nDecision\n\nKeep Stripe Billing for the 2026 release and build only a thin export service. Stop Meterline.\n\nRationale\n\nA custom service does not reduce reconciliation work enough to justify Q2 delivery risk.\n\nOpen questions\n\nWho owns the export schema?","notion","Meterline decision","meterline_old","meterline_new","decision_format")
    p("2026-04-20","09:44","morning quick atlus one devika shah joins the pod today and owns beta and launch test plans","Morning—quick Atlas one. Devika Shah joins the pod today and owns the beta and launch test plans.","slack","#atlas-delivery","devika_owner","slack_opening")
    p("2026-05-04","10:26","q three pricing page starts today jonas reed writes first two copy passes im internal product owner","The Q3 pricing-page project starts today. Jonas Reed will write the first two copy passes; I’m the internal product owner.","notion","Q3 pricing","pricing_owner_old")
    p("2026-05-07","11:18","hi prea atlus client beta is eighteenth may production launch twenty second june new paragraph can you confirm support labels by tuesday best meera","Hi Priya,\n\nThe Atlas client beta is 18 May, and production launch is 22 June.\n\nCould you confirm the support labels by Tuesday?\n\nBest,\nMeera","outlook","client-email","atlas_dates","email_prose","email_signoff")
    p("2026-05-12","16:03","change leverage the existing components to use the existing components","Change “leverage the existing components” to “use the existing components.”","notion","Atlas copy","word_use")
    p("2026-05-18","10:07","atlus beta bug route invoice pdf blank on safari devika own by noon","Atlas beta bug: invoice PDF is blank on Safari. Devika owns the fix by noon.","slack","#atlas-delivery","beta_episode","assignment_style")
    p("2026-05-18","10:11","atlas beta bug invoice p d f blank in safari devika please take it by twelve","Atlas beta bug: invoice PDF is blank on Safari. Devika owns the fix by noon.","slack","#atlas-delivery","beta_episode","near_duplicate_beta")
    p("2026-05-18","10:13","sorry retry atlus beta invoice pdf blank safari devika owns fix noon","Atlas beta bug: invoice PDF is blank on Safari. Devika owns the fix by noon.","slack","#atlas-delivery","beta_episode","near_duplicate_beta")
    p("2026-05-21","20:49","atlus beta review twenty first may decision safari pdf fix ships actions devika regression by friday aaron deploy monday","Atlas beta review, 21 May. Decision: ship the Safari PDF fix. Actions: Devika to complete regression by Friday; Arun to deploy Monday.","zoom","Atlas client review","beta_episode","recap_order")
    p("2026-05-26","14:42","move harbour pilot from eight june to thirteenth july omar update participant holds by thursday","Move the Harbor pilot from 8 June to 13 July. Omar, update the participant holds by Thursday.","slack","#harbor-pilot","harbor_date_old","harbor_date_new","assignment_style")
    p("2026-05-28","16:32","pricing review decision no three named packages use two engagement models fixed scope discovery and retained product work talk to us pricing","Pricing review decision, 28 May: remove the three named packages. Use two engagement models—fixed-scope discovery and retained product work—with “Talk to us” pricing.","zoom","Q3 pricing review","pricing_old","pricing_new")
    p("2026-05-29","15:54","priya hand off today is her last day at acne ria ragavan has the coordination threads elliot has final launch approval","Priya handoff, 29 May. Today is her last day at Acme. Ria Raghavan has the coordination threads; Elliot Barnes has final launch approval.","zoom","Acme handoff","contact_old","contact_new","elliot_approver","people_disambiguation")
    p("2026-06-01","09:39","morning quick pricing one sophia takes final page design now jonas contract ended yesterday share accessibility pass by friday","Morning—quick pricing one. Sofia takes over final page design now that Jonas’s contract ended yesterday. Please share the accessibility pass by Friday.","slack","#design-review","pricing_owner_new","slack_opening","assignment_style")
    p("2026-06-01","11:04","hi ria thanks for taking over coordination new paragraph can you confirm thursday at three g m t for the atlus review best meera","Hi Ria,\n\nThanks for taking over coordination.\n\nCould you confirm Thursday at 15:00 GMT for the Atlas review?\n\nBest,\nMeera","outlook","client-email","contact_new","review_slot_new","email_prose","email_signoff")
    p("2026-06-04","20:52","atlus review fourth june ria aaron sophia devika me decision launch stays twenty second action ria confirm fleet list monday","Atlas review, 4 June. Attendees: Ria, Arun, Sofia, Devika, Meera. Decision: launch remains 22 June. Action: Ria to confirm the fleet list by Monday.","zoom","Atlas client review","contact_new","atlas_dates","episode_review_0604","recap_order")
    p("2026-06-09","15:17","pricing legal review approved two engagement models talk to us publication second july one accessibility check open","Pricing legal review, 9 June. Approved: two engagement models with “Talk to us” pricing. Publication target: 2 July. One accessibility check remains open.","zoom","Q3 pricing review","pricing_new","pricing_publish")
    p("2026-06-11","10:28","replace leverage our research with use our research","Replace “leverage our research” with “use our research.”","notion","Q3 pricing","word_use")
    p("2026-06-17","14:53","heading context colon launch readiness heading decision colon production launch twenty second june heading rationale colon beta blockers closed heading open questions colon two non blocking defects","Context\n\nAtlas launch readiness.\n\nDecision\n\nProduction launch remains 22 June.\n\nRationale\n\nAll beta blockers are closed.\n\nOpen questions\n\nTwo non-blocking defects remain.","notion","Atlas launch decision","atlas_dates","decision_format")
    p("2026-06-22","18:12","atlus production launched today two non blocking defects stay in monitoring","Atlas launched to production on 22 June. Two non-blocking defects remain in monitoring.","slack","#atlas-delivery","atlas_launch")
    p("2026-06-24","12:23","harbour build check invite identity and first login are in scope pilot thirteenth july training payroll out","Harbor build check: invitations, identity checks, and first login are in scope for the 13 July pilot. Training and payroll are out of scope.","notion","Harbor brief","harbor_scope","harbor_date_new")
    p("2026-06-25","20:43","atlus review twenty fifth june ria says close out is seventh july","Atlas review, 25 June. Ria confirmed the closeout is 7 July.","zoom","Atlas client review","atlas_closeout","contact_new")
    p("2026-06-29","10:09","morning quick pricing one sophia complete accessibility check by tuesday publish stays second july","Morning—quick pricing one. Sofia, complete the accessibility check by Tuesday. Publication remains 2 July.","slack","#design-review","pricing_publish","assignment_style","slack_opening")
    p("2026-06-30","16:41","six month closeout atlus launched monitoring two non blockers harbour active july thirteen pricing approved july two meter line killed cedar archived","Six-month closeout: Atlas has launched and is monitoring two non-blocking defects; Harbor is active for the 13 July pilot; the pricing page is approved for 2 July; Meterline was stopped; Cedar is archived.","notion","portfolio closeout","portfolio_current")
    # Deliberate unresolved stated contradiction: two user-authored records, no correction.
    p("2026-03-18","12:09","atlas support retention is ninety days per the client note","Atlas support-log retention is 90 days, per the client note.","notion","Atlas operations","retention_conflict")
    p("2026-03-20","09:58","confirm atlas support logs retention is one hundred twenty days","Atlas support-log retention is 120 days.","slack","#atlas-delivery","retention_conflict")


MUNDANE = {
    "slack": [
        ("okay acknowledge the thread", "Acknowledged in the thread."),
        ("right moving the link into the channel", "Moving the link into the channel."),
        ("thanks seen ill reply after stand up", "Thanks, seen. I’ll reply after stand-up."),
        ("quick one the room is cedar not c deck", "Quick one: the room is Cedar, not C-deck."),
        ("uploading the latest screen recording now", "Uploading the latest screen recording now."),
        ("no action just closing the loop", "No action—just closing the loop."),
        ("can someone paste the doc link here", "Can someone paste the document link here?"),
        ("actually ignore my last typo the label is correct", "Ignore my last typo; the label is correct."),
    ],
    "notion": [
        ("scratch rewrite the opening sentence its too long", "Scratch note: rewrite the opening sentence; it is too long."),
        ("add screenshot placeholder below this paragraph", "Add a screenshot placeholder below this paragraph."),
        ("move this paragraph above the table", "Move this paragraph above the table."),
        ("check heading levels before sharing", "Check heading levels before sharing."),
        ("todo clean up duplicate comments", "To do: clean up duplicate comments."),
        ("note this is draft wording not a decision", "Note: this is draft wording, not a decision."),
    ],
    "outlook": [
        ("hi thanks for sending this ill review and come back tomorrow best meera", "Hi,\n\nThanks for sending this. I’ll review it and come back tomorrow.\n\nBest,\nMeera"),
        ("hi attaching the version we discussed no action needed today best meera", "Hi,\n\nI’m attaching the version we discussed. No action is needed today.\n\nBest,\nMeera"),
        ("hi the link in my previous note was wrong please use this one best meera", "Hi,\n\nThe link in my previous note was wrong. Please use this one.\n\nBest,\nMeera"),
    ],
    "scratch": [
        ("remember charger and umbrella", "Remember charger and umbrella."),
        ("buy coffee filters on the way home", "Buy coffee filters on the way home."),
        ("book title the design of everyday things", "Book title: The Design of Everyday Things."),
        ("move dentist reminder to phone list", "Move the dentist reminder to the phone list."),
        ("groceries coriander yoghurt lemons", "Groceries: coriander, yoghurt, lemons."),
    ],
}


def is_gap(d: date) -> bool:
    return date(2026,4,13) <= d <= date(2026,4,17)


def fill_to_500() -> None:
    planted_dates = Counter(r["occurred_at"][:10] for r in records)
    days = []
    d = date(2026,1,5)
    while d <= date(2026,6,30):
        if d.weekday() < 5 and not is_gap(d):
            base = [4,3,4,5,3][d.weekday()]
            if date(2026,1,26) <= d <= date(2026,1,30): base = 1
            if date(2026,2,23) <= d <= date(2026,2,27): base = 2
            if date(2026,5,18) <= d <= date(2026,5,22): base = 7
            if date(2026,6,1) <= d <= date(2026,6,5): base = 2
            days.extend([d] * max(0, base - planted_dates[d.isoformat()]))
        d += timedelta(days=1)
    # A few quiet Sunday scratch records.
    days += [date(2026,1,18), date(2026,2,8), date(2026,3,29), date(2026,5,10), date(2026,6,14)]
    while len(days) < 500 - len(records):
        eligible = [date(2026,1,5)+timedelta(days=i) for i in range(177)
                    if (date(2026,1,5)+timedelta(days=i)).weekday() < 5 and not is_gap(date(2026,1,5)+timedelta(days=i))]
        days.append(RNG.choice(eligible))
    RNG.shuffle(days)
    days = days[:500-len(records)]
    for d in days:
        if d.weekday() == 6:
            app = "scratch"
        else:
            app = RNG.choices(["slack","notion","outlook","scratch"],[58,22,12,8])[0]
        raw, fmt = RNG.choice(MUNDANE[app])
        if app == "slack":
            channel = RNG.choice(["#atlas-delivery","#design-review","#product-strategy","#harbor-pilot"])
            hh = RNG.choice([9,10,11,12,14,15,16,17])
            application = "slack"
        elif app == "outlook":
            channel, application, hh = "client-email", "outlook", RNG.choice([10,11,16,17])
        elif app == "notion":
            channel, application, hh = RNG.choice(["Atlas notes","Harbor notes","pricing draft","scratchpad"]), "notion", RNG.choice([13,14,15,16])
        else:
            channel, application, hh = None, "private-scratch", RNG.choice([8,18,19,20,21])
        minute = RNG.randrange(0,60)
        add(d.isoformat(), f"{hh:02d}:{minute:02d}", raw, fmt, application, channel)


GROUND = [
    ("gt_identity_role","fact","identity_role","Meera Sethi is Product Lead at Ternary Studio.","Direct statement in one passing introduction."),
    ("gt_join_date","fact","join_date","Meera joined Ternary Studio on 14 August 2023.","Single-occurrence fact; recover from the introduction."),
    ("gt_atlas_owners","fact","atlas_owners","Arun Menon owns Atlas backend; Sofia Martins owns design; Priya Raghavan is the initial Acme contact.","Split the compound statement into atomic entity relations while preserving one source."),
    ("gt_atlas_scope","fact","atlas_scope_part1","Atlas replaces Acme’s legacy fleet-manager portal and covers vehicle status, driver access, invoices, and support.","Recover the project purpose and four scope elements together."),
    ("gt_cedar","episode","cedar_fact+cedar_episode+cedar_complete","Cedar was the Northwind analytics handoff; walkthrough was 29 January and access was confirmed 2 February, after which it was archived.","Combine three dated records; do not infer that Cedar remains active."),
    ("gt_review_slot","fact","review_slot_old+review_slot_new","Current: Thursdays at 15:00 GMT from 12 February 2026. Superseded: Tuesdays at 15:00 GMT through 11 February.","Order by occurred_at and retain the old cadence as superseded history."),
    ("gt_arun_role","fact","arun_lead_implied+arun_lead_current","Arun Menon became Atlas Technical Lead on 2 March 2026 and owns release sign-off.","Combine two implied uses with the later explicit title confirmation."),
    ("gt_manager","fact","manager_old+manager_new","Current from 16 March: Leena Iyer. Before then: Nandini Rao; Nandini remains Atlas sponsor.","Temporal supersession with explicit change date; retain both historical values."),
    ("gt_meterline","fact","meterline_old+meterline_new","Current from 9 April: keep Stripe Billing and build a thin export service; Meterline is stopped. Superseded: build Meterline in Q2.","Decision reversal; current answer must not blend old and new."),
    ("gt_harbor_scope","fact","harbor_scope","Harbor covers invitations, identity checks, and first login; it excludes training and payroll.","Combine the proposal and later build check."),
    ("gt_harbor_owners","fact","harbor_owners","Meera is product lead; Omar runs research logistics; Sofia owns interaction design.","Recover work-level ownership relations."),
    ("gt_harbor_date","episode","harbor_date_old+harbor_date_new","Current pilot date: 13 July 2026, changed on 26 May from 8 June.","Temporal supersession; cite the reschedule and later confirmation."),
    ("gt_figma_project","fact","figma_new","Current design workspace is `Acme Product / Atlas` from 6 April; earlier workspace was `ACME / Atlas 2026` (persona prior state).","Infer current workspace from repeated later paths; corpus itself only supports the new value."),
    ("gt_devika","fact","devika_owner","Devika Shah joined the Atlas pod on 20 April and owns beta and launch test plans.","Single passing assignment."),
    ("gt_atlas_dates","episode","atlas_dates+atlas_launch","Atlas client beta was 18 May and production launch occurred 22 June 2026.","Combine planned dates with the launch completion record."),
    ("gt_beta_bug","episode","beta_episode","On 18 May during Atlas beta, the Safari invoice-PDF bug was routed to Devika; on 21 May the team decided to ship the fix.","Identify by date, Slack/Zoom application context, and bug topic."),
    ("gt_beta_dedup","episode","near_duplicate_beta","The 18 May Safari PDF bug-routing messages are retries/near-duplicates and should collapse to one memory.","Semantic near-duplicate merge; distinct transcript IDs must not inflate independent facts."),
    ("gt_pricing_structure","fact","pricing_old+pricing_new","Current from 28 May: two engagement models with ‘Talk to us’ pricing. Superseded: three named packages with indicative prices.","Decision reversal with dated supersession."),
    ("gt_pricing_owner","fact","pricing_owner_old+pricing_owner_new","Jonas Reed wrote the first two copy passes; Sofia Martins owns final page design from 1 June after Jonas’s contract ended.","Combine handoff facts across May and June."),
    ("gt_contact","fact","contact_old+contact_new","Current from 1 June: Ria Raghavan is Acme coordination contact. Priya Raghavan was the prior contact and left on 29 May.","Infer handoff from departure plus repeated later addressing; disambiguate similar names by role/time."),
    ("gt_elliot","fact","elliot_approver","Elliot Barnes is the final Acme launch approver after Priya’s departure.","Single passing fact in the handoff recap."),
    ("gt_pricing_publish","episode","pricing_publish","The pricing page is approved for publication on 2 July, pending one accessibility check.","Combine legal review and final assignment."),
    ("gt_atlas_launch","episode","atlas_launch+atlas_closeout","Atlas launched 22 June, has two non-blocking defects in monitoring, and has a 7 July closeout.","Combine launch and review records."),
    ("gt_retention_conflict","fact","retention_conflict","Unresolved contradiction: Atlas support-log retention is stated as both 90 and 120 days.","Surface both stated values and abstain from choosing; no correction resolves them."),
    ("gt_pref_slack_opening","preference","slack_opening","Observed: first Slack messages before noon tend to open ‘Morning—’ plus a short topic label.","Infer only from repeated demonstrations; keep observed, not stated."),
    ("gt_pref_assignments","preference","assignment_style","Observed: actionable Slack requests usually name an owner and explicit weekday/date.","Aggregate repeated independent demonstrations; acknowledgements are neutral exceptions."),
    ("gt_pref_email_prose","preference","email_prose","Observed: client emails use short prose paragraphs with context before the ask.","Infer from repeated external-email examples; one-line mundane emails are exceptions."),
    ("gt_pref_signoff","preference","email_signoff","Observed: client emails close ‘Best, Meera’; Slack and documents do not.","Infer across external email records only; never promote to stated."),
    ("gt_pref_recap_order","preference","recap_order","Observed: meeting recaps place decisions before actions.","Repeated structure across dated recaps."),
    ("gt_pref_decision_format","preference","decision_format","Observed: decision documents use Context, Decision, Rationale, Open questions in that order.","Repeated Notion document formatting; observed only."),
    ("gt_pref_word_use","preference","word_use","Observed: Meera replaces ‘leverage’ with ‘use’ in her drafts.","Two independent revisions demonstrate the preference without stating a rule."),
    ("gt_people_disambiguation","fact","people_disambiguation","Priya and Ria Raghavan are different Acme contacts; Arun Menon is Ternary technical lead and Varun Menon is Acme security engineer.","Use organisation, role, project, and time—not phonetics alone—to resolve ASR confusions."),
    ("gt_portfolio_current","fact","portfolio_current","At 30 June: Atlas launched; Harbor active for 13 July; pricing approved for 2 July; Meterline stopped; Cedar archived.","Current-state portfolio check corroborating earlier distributed facts."),
]


def write() -> None:
    records.sort(key=lambda r: (r["occurred_at"], r["transcript_id"]))
    # IDs encode authored order, making provenance easier to inspect.
    old_to_new = {}
    for i, rec in enumerate(records, 1):
        old, new = rec["transcript_id"], f"meera_2026_{i:04d}"
        old_to_new[old] = new
        rec["transcript_id"] = new
    for k, ids in labels.items():
        labels[k] = [old_to_new[x] for x in ids]
    OUT.write_text(json.dumps({"records": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    items = []
    for iid, typ, label_expr, answer, recovery in GROUND:
        ids = []
        for label in label_expr.split("+"):
            ids.extend(labels[label])
        items.append({"id": iid, "type": typ, "record_ids": list(dict.fromkeys(ids)),
                      "correct_answer": answer, "recovery": recovery})
    GT.write_text(json.dumps({"corpus":"fixtures/development-500.json","persona":"Meera Sethi",
                              "period":{"start":"2026-01-05","end":"2026-06-30","timezone":"Asia/Kolkata"},
                              "items":items}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    planted()
    fill_to_500()
    assert len(records) == 500
    assert all(r["raw_asr"] != r["formatted_text"] for r in records)
    write()
