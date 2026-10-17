"""Generates mods/PeopleFirst/hearts/*.json: v0.2 "Hearts" (concept §4.2, §4.3, §4.5, §6.2).

Relationship stages build on v0.1's sweethearts (u_pf_has_sweet / u_pf_sweet): u_pf_rel_stage 1 sweethearts, 2 partners, 3 married.
Like everything else, these systems only read views and report moments; the spine does the rest (marriage slows drift there).
Hooks called from life/*.json: PF_HEART_fire (fire beat), PF_HEART_jealousy (a glance), PF_HEART_grief / PF_HEART_avatar_grief
(a death), PF_HEART_band_viewer (off-screen camp), PF_JOURNAL_add (the spine, when the avatar keeps a memory).

Usage:  python tools/gen_hearts.py mods/PeopleFirst/hearts
"""
import json, os, sys

OUT = sys.argv[1]
def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
def ctx(n): return {"context_val": n}
def eoc(id_, effect, comment=None, condition=None, **extra):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    o.update(extra)
    if condition: o["condition"] = condition
    o["effect"] = effect
    return o
def say(text, t="info"): return {"u_message": text, "type": t}
def hsay(text, home, t="info"):
    """A line that changes when tonight's evening is indoors at home (v0.4) instead of at a fire."""
    return {"if": {"math": ["value_or(pf_eve_home, 0) == 1"]}, "then": [say(home, t)], "else": [say(text, t)]}
def name_into(gvar, tag="<u_name>"): return {"set_string_var": tag, "target_var": g(gvar), "parse_tags": True}
def regname(uid_global, target):
    """Name of a person from the directory (works without a talker, even for the dead)."""
    return [{"set_string_var": "pf_name_<global_val:%s>" % uid_global, "target_var": ctx("nref"), "parse_tags": True},
            {"copy_var": {"var_val": "nref"}, "target_var": g(target)}]
def cooldown_ok_c(var, dur):
    return {"or": [m(f"time_since({var}) < 0"), m(f"time_since({var}) > time('{dur}')")]}
def line(key): return {"run_eocs": "PF_SAY_heart", "alpha_talker": "avatar", "variables": {"line": key}}
def morale(kind, bonus, maxb, dur, decay):
    return {"u_add_morale": kind, "bonus": bonus, "max_bonus": maxb, "duration": dur, "decay_start": decay}
VNAMES = [{"set_string_var": f"u_pf_v_<global_val:pf_m_other>_{suf}", "target_var": ctx(c), "parse_tags": True}
          for c, suf in (("rw", "w"), ("rt", "t"), ("rx", "x"), ("rpw", "pw"), ("rpt", "pt"), ("rl", "l"), ("ra", "a"), ("rpa", "pa"), ("rc", "c"), ("rf", "f"))]
ON = "value_or(pf_set_jealousy, 1) == 1"
MOURNING = "time('now') < value_or(u_pf_mourn_until, 0)"

def find_at_fire(uid_global, out):
    """Index of the person with uid in global uid_global among tonight's fire-goers (-1 = you, -9 = not here)."""
    eff = [m(f"{out} = -9")]
    for j in range(6):
        eff.append({"if": {"and": [m(f"pf_fire_n > {j}"), {"compare_string": [g(uid_global), g(f"pf_fire_u_{j}")]}]},
                    "then": [m(f"{out} = {j}")]})
    eff.append({"if": {"and": [m("pf_fire_av_here"), {"compare_string": [g(uid_global), "AVATAR"]}]}, "then": [m(f"{out} = -1")]})
    return eff

files = {}

# ============================================================ MORALE (what the player feels; NPCs carry it too)
files["morale.json"] = [
    {"type": "morale_type", "id": "PF_morale_together", "text": "Together"},
    {"type": "morale_type", "id": "PF_morale_wed", "text": "Just married"},
    {"type": "morale_type", "id": "PF_morale_grief", "text": "Grieving"},
    {"type": "morale_type", "id": "PF_morale_heartbreak", "text": "Heartbroken"},
]

# ============================================================ COUPLES AT THE FIRE (stages, proposals, weddings, breakups)
files["couples.json"] = [
    eoc("PF_HEART_fire", [
        m("pf_ht_done = 0"), m("pf_fi = 0"),
        {"run_eocs": "PF_HEART_fire_i", "condition": {"and": [m("pf_fi < pf_fire_n"), m("pf_ht_done < 2")]}, "iterations": 10},
        {"run_eocs": "PF_HEART_avatar_left_check"},
    ], "u = avatar, during the evening (after the romance beat).  Couples at the fire move along: sweethearts become partners, partners propose, and couples who have soured break up.  At most two such scenes a night."),
    eoc("PF_HEART_fire_i", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"run_eocs": "PF_HEART_fire_one", "alpha_talker": {"var_val": "ri"}},
        m("pf_fi += 1"),
    ]),
    eoc("PF_HEART_fire_one", [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_ht_s")},
    ] + find_at_fire("pf_ht_s", "pf_ht_sj") + [
        {"if": m("pf_ht_sj != -9"), "then": [
            m("u_pf_ht_beat = pf_beat_id"),
            {"copy_var": g("pf_ht_s"), "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read"},
            m("pf_ht_aw = pf_read_w"), m("pf_ht_at = pf_read_t"), m("pf_ht_aa = pf_read_a"), m("pf_ht_ax = pf_read_x"),
            {"if": m("pf_ht_sj == -1"),
             "then": [{"run_eocs": "PF_HEART_couple", "beta_talker": "avatar"}],
             "else": [{"set_string_var": "pf_fire_c_<global_val:pf_ht_sj>", "target_var": ctx("rj"), "parse_tags": True},
                      {"run_eocs": "PF_HEART_couple", "beta_talker": {"var_val": "rj"}}]}]},
    ], "u = someone at the fire who is in a relationship.  If their partner is here too, look at the relationship through their eyes.",
        condition={"and": [m("value_or(u_pf_has_sweet, 0) == 1"), m("value_or(u_pf_ht_beat, -1) != pf_beat_id"), {"not": {"u_has_trait": "PF_CHILD"}}]}),
    eoc("PF_HEART_couple", [
        m("pf_ht_st = value_or(u_pf_rel_stage, 1)"), m("pf_ht_before = pf_ht_done"),
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        {"if": {"and": [m(ON), {"or": [m("pf_ht_ax >= 35 + 15 * pf_ht_st"), m("pf_ht_aa < 25 - 5 * pf_ht_st"), m("pf_ht_aw < 10")]}]},
         "then": [m("pf_ht_done += 1"), {"run_eocs": "PF_HEART_breakup"}],
         "else": [{"if": {"and": [m("pf_ht_st == 1"), m("time_since(u_pf_sweet_since) >= time('7 d')"), m("pf_ht_aw >= 45"), m("pf_ht_aa >= 45")]},
                   "then": [m("pf_ht_done += 1"), {"run_eocs": "PF_HEART_partnered"}],
                   "else": [{"if": {"and": [m("pf_ht_st == 2"), m("time_since(value_or(u_pf_stage_since, 0)) >= time('14 d')"),
                                            m("pf_ht_aw >= 65"), m("pf_ht_at >= 55"), m("pf_ht_aa >= 55"), m("value_or(u_pf_commit, 1) != 3"),
                                            m("value_or(u_pf_engaged, 0) == 0"),
                                            cooldown_ok_c("u_pf_prop_last", "14 d")]},
                             "then": [m("pf_ht_done += 1"), m("u_pf_prop_last = time('now')"), {"run_eocs": "PF_HEART_propose"}]}]}]},
        {"if": m("pf_ht_done > pf_ht_before"), "then": [m("n_pf_ht_beat = pf_beat_id")], "else": [{"run_eocs": "PF_FAM_try_conceive"}]},
    ], "Alpha = one partner (whose view was just read into pf_ht_a*), beta = the other (an NPC at the fire, or you).  Breakup if tension passes 35 + 15 per stage, attraction falls under 25 - 5 per stage, or warmth under 10 (married couples hold on longest).  Otherwise sweethearts of a week with warmth and attraction 45+ become partners, and partners of two weeks with warmth 65+, trust 55+ and attraction 55+ propose (never the wandering-eyed)."),
    eoc("PF_HEART_partnered", [
        m("u_pf_rel_stage = 2"), m("n_pf_rel_stage = 2"), m("u_pf_stage_since = time('now')"), m("n_pf_stage_since = time('now')"),
        {"if": "npc_is_avatar", "then": [line("partner_you")], "else": [line("partner_npc")]},
        {"run_eocs": "PF_MK_partnered"},
    ], "Alpha and beta stop pretending: partners now."),
    eoc("PF_HEART_propose", [
        {"if": "npc_is_avatar",
         "then": [{"if": m("value_or(pf_set_romance, 2) == 2"), "then": [
             {"u_set_talker": g("pf_prop_who")},
             {"run_eocs": "PF_HEART_open_propose", "alpha_talker": "avatar", "beta_talker": "u"}]}],
         "else": [{"run_eocs": "PF_HEART_answer_npc", "alpha_talker": "npc", "beta_talker": "u"},
                  {"if": m("pf_ht_yes == 1"),
                   "then": [{"run_eocs": "PF_HEART_engage"}, line("engaged_npc")],
                   "else": [line("prop_no_npc"), {"run_eocs": "PF_MK_proposal_declined", "alpha_talker": "npc", "beta_talker": "u"}]}]},
    ], "Alpha proposes to beta.  To you it's a conversation; between NPCs the other answers from their own heart."),
    eoc("PF_HEART_answer_npc", [
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_ht_yes = (pf_read_w >= 60) * (pf_read_a >= 50) * (pf_read_t >= 50) * (value_or(u_pf_commit, 1) != 3)"),
    ], "u = the one being proposed to, npc = the one proposing."),
    eoc("PF_HEART_engage", [
        m("u_pf_engaged = 1"), m("n_pf_engaged = 1"),
        m("u_pf_wed_t = time('now') + time('1 d')"), m("n_pf_wed_t = time('now') + time('1 d')"),
        m("pf_engagements_total = value_or(pf_engagements_total, 0) + 1"),
    ], "Alpha and beta are engaged.  The wedding is a whole evening of its own, from a day later, on the first calm night (PF_HEART_wedding_try)."),
    eoc("PF_HEART_wedding_try", [
        m("pf_fi = 0"), m("pf_fire_wedding = 0"),
        {"run_eocs": "PF_HEART_wed_try_i", "condition": {"and": [m("pf_fi < pf_fire_n"), m("pf_fire_wedding == 0")]}, "iterations": 10},
    ], "u = you, at the start of the evening (after a remembrance would have claimed it).  If an engaged couple is at the fire and the day has come, tonight is their wedding.",
        condition=m("pf_fire_service == 0")),
    eoc("PF_HEART_wed_try_i", [
        {"set_string_var": "pf_fire_c_<global_val:pf_fi>", "target_var": ctx("ri"), "parse_tags": True},
        {"run_eocs": "PF_HEART_wed_try_one", "alpha_talker": {"var_val": "ri"}},
        m("pf_fi += 1"),
    ]),
    eoc("PF_HEART_wed_try_one", [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_ht_s")},
    ] + find_at_fire("pf_ht_s", "pf_ht_sj") + [
        {"if": m("pf_ht_sj == -1"), "then": [m("pf_fire_wedding = 1"), {"run_eocs": "PF_HEART_ceremony", "beta_talker": "avatar"}]},
        {"if": m("pf_ht_sj >= 0"), "then": [
            m("pf_fire_wedding = 1"),
            {"set_string_var": "pf_fire_c_<global_val:pf_ht_sj>", "target_var": ctx("rj"), "parse_tags": True},
            {"run_eocs": "PF_HEART_ceremony", "beta_talker": {"var_val": "rj"}}]},
    ], condition={"and": [m("value_or(u_pf_engaged, 0) == 1"), m("value_or(u_pf_has_sweet, 0) == 1"), m("time('now') >= value_or(u_pf_wed_t, 0)"),
                          {"not": m(MOURNING)}]}),
    eoc("PF_HEART_ceremony", [
        m("u_pf_engaged = 0"), m("n_pf_engaged = 0"),
        name_into("pf_say_a"), name_into("pf_say_b", "<npc_name>"),
        {"run_eocs": "PF_HEART_wed"},
        {"if": "npc_is_avatar",
         "then": [line("wedding_you"), {"run_eocs": "PF_HEART_wed_morale", "alpha_talker": "avatar"}],
         "else": [line("wedding_npc")]},
        line("wedding_feast"),
    ], "Alpha and beta marry, and the evening is theirs: no ordinary activities tonight."),
    eoc("PF_HEART_wed_morale", [morale("PF_morale_wed", 20, 30, "3 d", "1 d")]),
    eoc("PF_HEART_wed", [
        m("u_pf_rel_stage = 3"), m("n_pf_rel_stage = 3"), m("u_pf_stage_since = time('now')"), m("n_pf_stage_since = time('now')"),
        m("pf_m_str_in = 85"), {"run_eocs": "PF_MK_wedding"},
        m("pf_weddings_total = value_or(pf_weddings_total, 0) + 1"),
        {"set_string_var": "wed", "target_var": g("pf_ev_new_kind")},
        {"set_string_var": "<u_name> and <npc_name>", "target_var": g("pf_ev_new_name"), "parse_tags": True},
        m("pf_ev_new_you = 0"),
        {"if": "u_is_avatar", "then": [m("pf_ev_new_you = 1"), name_into("pf_ev_new_youname", "<npc_name>")]},
        {"if": "npc_is_avatar", "then": [m("pf_ev_new_you = 1"), name_into("pf_ev_new_youname")]},
        {"run_eocs": "PF_HEART_event_add"},
    ], "Alpha and beta marry.  Strength 85: everyone who sees it remembers it (witnesses), and the spine slows their drift from now on."),
    eoc("PF_HEART_open_propose", [{"open_dialogue": {"topic": "TALK_PF_PROPOSE"}}],
        "Alpha = you.  The proposer is in pf_prop_who (a topic dialogue talks to an empty talker)."),
    eoc("PF_HEART_you_yes", [
        {"run_eocs": "PF_HEART_engage", "alpha_talker": "npc", "beta_talker": "u"},
        morale("PF_morale_wed", 10, 20, "2 d", "1 d"),
        line("engaged_you"),
    ], "In the proposal dialogue: u = you, npc = them (via pf_prop_who)."),
    eoc("PF_HEART_you_notyet", [
        {"run_eocs": "PF_MK_proposal_declined", "beta_talker": "npc"},
        say("<global_val:pf_say_a> nods.  \"Okay.  I can wait.\""),
    ]),
    eoc("PF_HEART_you_no", [
        m("pf_m_str_in = 60"), {"run_eocs": "PF_MK_proposal_declined", "beta_talker": "npc"},
        hsay("<global_val:pf_say_a> looks at the fire for a long time.  \"Right.  Okay.\"", "<global_val:pf_say_a> looks at the floor for a long time.  \"Right.  Okay.\"", "bad"),
    ]),
    eoc("PF_HEART_breakup", [
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": {"u_val": "pf_ex"}}, {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_ex"}},
        m("u_pf_has_sweet = 0"), m("n_pf_has_sweet = 0"), m("u_pf_rel_stage = 0"), m("n_pf_rel_stage = 0"),
        m("u_pf_awk_until = time('now') + time('5 d')"), m("n_pf_awk_until = time('now') + time('5 d')"),
        {"set_string_var": "none", "target_var": {"u_val": "pf_sweet"}}, {"set_string_var": "none", "target_var": {"npc_val": "pf_sweet"}},
        {"run_eocs": "PF_MK_breakup"},
        {"if": "npc_is_avatar",
         "then": [line("breakup_you"), {"run_eocs": "PF_HEART_heartbreak", "alpha_talker": "avatar"}],
         "else": [line("breakup_npc")]},
        m("pf_breakups_total = value_or(pf_breakups_total, 0) + 1"),
    ], "Alpha ends it with beta.  Both remember who it was (u_pf_ex); awkward for five days.  Reconciliation needs nothing special: if attraction survives, the usual confession can happen again."),
    eoc("PF_HEART_heartbreak", [morale("PF_morale_heartbreak", -15, -25, "2 d", "1 d")], "u = whoever's heart just broke."),
    eoc("PF_HEART_avatar_left_check", [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_ht_s")},
    ] + find_at_fire("pf_ht_s", "pf_ht_sj") + [
        {"if": m("pf_ht_sj >= 0"), "then": [
            {"set_string_var": "pf_fire_c_<global_val:pf_ht_sj>", "target_var": ctx("rj"), "parse_tags": True},
            {"run_eocs": "PF_HEART_left_you", "alpha_talker": {"var_val": "rj"}, "beta_talker": "avatar"}]},
    ], "u = you.  If the one you think you're with is at the fire and has moved on (with someone else, or with no one), it's over, and tonight everyone can see it.",
        condition=m("value_or(u_pf_has_sweet, 0) == 1")),
    eoc("PF_HEART_left_you", [
        name_into("pf_say_a"),
        m("n_pf_has_sweet = 0"), m("n_pf_rel_stage = 0"), {"set_string_var": "none", "target_var": {"npc_val": "pf_sweet"}},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_ex"}},
        {"run_eocs": "PF_MK_breakup"},
        {"if": m("value_or(u_pf_has_sweet, 0) == 1"), "then": [{"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_ht_new")}] + regname("pf_ht_new", "pf_say_b") + [line("left_you_for")],
         "else": [line("left_you")]},
        {"run_eocs": "PF_HEART_heartbreak", "alpha_talker": "avatar"},
    ], "Alpha = the one who moved on, beta = you.",
        condition={"or": [m("value_or(u_pf_has_sweet, 0) == 0"), {"not": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}}]}),
    # ---- the player acts (People menu)
    eoc("PF_HEART_you_propose", [
        {"run_eocs": "PF_HEART_answer_npc", "alpha_talker": "npc", "beta_talker": "u"},
        name_into("pf_say_a", "<npc_name>"),
        {"if": m("pf_ht_yes == 1"),
         "then": [{"run_eocs": "PF_HEART_engage"}, morale("PF_morale_wed", 10, 20, "2 d", "1 d"),
                  say("<npc_name> laughs, and cries a little, and says yes.  The wedding will be the first quiet evening after tomorrow.", "good")],
         "else": [{"run_eocs": "PF_MK_proposal_declined", "alpha_talker": "npc", "beta_talker": "u"},
                  {"run_eocs": "PF_HEART_why_not", "alpha_talker": "npc"}]},
    ], "u = you, npc = your partner.  They answer from their own heart (warmth 60+, attraction 50+, trust 50+; the wandering-eyed never)."),
    eoc("PF_HEART_why_not", [
        {"if": m("value_or(u_pf_commit, 1) == 3"),
         "then": [{"run_eocs": "PF_SAY_heart", "alpha_talker": "avatar", "variables": {"line": "prop_wander"}}],
         "else": [{"run_eocs": "PF_SAY_heart", "alpha_talker": "avatar", "variables": {"line": "prop_notyet"}}]},
    ]),
    eoc("PF_HEART_you_end", [
        {"run_eocs": "PF_HEART_their_side", "alpha_talker": "npc"},
        name_into("pf_say_a", "<npc_name>"),
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": {"u_val": "pf_ex"}}, {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_ex"}},
        m("u_pf_has_sweet = 0"), m("n_pf_has_sweet = 0"), m("u_pf_rel_stage = 0"), m("n_pf_rel_stage = 0"), m("n_pf_awk_until = time('now') + time('7 d')"),
        {"set_string_var": "none", "target_var": {"u_val": "pf_sweet"}}, {"set_string_var": "none", "target_var": {"npc_val": "pf_sweet"}},
        {"run_eocs": "PF_MK_breakup", "beta_talker": "npc"},
        {"if": m("pf_ht_aa >= 50"),
         "then": [say("<npc_name> stares at you.  \"…Okay.\"  They walk away before you can see their face.", "bad"),
                  {"run_eocs": "PF_HEART_heartbreak", "alpha_talker": "npc"}],
         "else": [say("<npc_name> nods slowly.  \"Yeah.  I think I knew.\"", "info")]},
        m("pf_breakups_total = value_or(pf_breakups_total, 0) + 1"),
    ], "u = you, npc = the one you're with.  How it lands depends on how they still feel."),
    eoc("PF_HEART_their_side", [
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        m("pf_ht_aw = pf_read_w"), m("pf_ht_aa = pf_read_a"), m("pf_ht_at = pf_read_t"),
    ], "u = an NPC.  Their view of you into pf_ht_a*."),
    # dialogue
    {"type": "talk_topic", "id": "TALK_PF_PROPOSE",
     "dynamic_line": "*takes a breath*  I've been carrying this around for weeks.  Marry me.  Here, tonight, with everyone watching.  Or tell me to shut up.  Either way.",
     "responses": [
         {"text": "Yes.", "effect": {"run_eocs": "PF_HEART_you_yes", "alpha_talker": "avatar", "beta_talker": g("pf_prop_who")}, "topic": "TALK_DONE"},
         {"text": "Not yet.  Ask me again.", "effect": {"run_eocs": "PF_HEART_you_notyet", "alpha_talker": "avatar", "beta_talker": g("pf_prop_who")}, "topic": "TALK_DONE"},
         {"text": "No.  I don't want that.", "effect": {"run_eocs": "PF_HEART_you_no", "alpha_talker": "avatar", "beta_talker": g("pf_prop_who")}, "topic": "TALK_DONE"}]},
]

# ============================================================ JEALOUSY (a glance, and who saw it)
files["jealousy.json"] = [
    eoc("PF_HEART_jealousy", [
        {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_jl_a")}, {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_jl_b")},
        name_into("pf_jl_an"), name_into("pf_jl_bn", "<npc_name>"),
        {"if": "npc_is_avatar", "then": [{"set_string_var": "you", "target_var": g("pf_jl_bn")}]},
        m("pf_jl_said = 0"),
        # 1. the one being looked at is taken: their partner, if here, sees it
        {"if": {"and": [m("value_or(n_pf_has_sweet, 0) == 1"), {"not": {"compare_string": [{"npc_val": "pf_sweet"}, g("pf_jl_a")]}}]}, "then": [
            {"copy_var": {"npc_val": "pf_sweet"}, "target_var": g("pf_jl_c")},
            m("pf_jl_str = value_or(n_pf_rel_stage, 1) >= 3 ? 25 : 50"),
            {"run_eocs": "PF_HEART_jealous_where"}]},
        # 2. the one looking is taken (a wandering eye): their partner, if here, sees it
        {"if": {"and": [m("pf_jl_said == 0"), m("value_or(u_pf_has_sweet, 0) == 1"), {"not": {"compare_string": [{"u_val": "pf_sweet"}, g("pf_jl_b")]}}]}, "then": [
            {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_jl_c")},
            m("pf_jl_str = 60"),
            {"run_eocs": "PF_HEART_jealous_where"}]},
    ], "u = someone making eyes at npc (another fire-goer, or you).  Whoever is with either of them, if they're at the fire, sees it and it sours their view of the one doing the looking (married people take it less hard about their spouse being looked at).",
        condition=m(ON)),
    eoc("PF_HEART_jealous_where", find_at_fire("pf_jl_c", "pf_jl_cj") + [
        {"if": m("pf_jl_cj == -1"), "then": [
            {"run_eocs": "PF_HEART_jealous_one", "alpha_talker": "avatar"}, m("pf_jl_said = 1"), line("jealous_you")]},
        {"if": m("pf_jl_cj >= 0"), "then": [
            {"set_string_var": "pf_fire_c_<global_val:pf_jl_cj>", "target_var": ctx("rc"), "parse_tags": True},
            {"run_eocs": "PF_HEART_jealous_one", "alpha_talker": {"var_val": "rc"}}, m("pf_jl_said = 1"), line("jealous_npc")]},
    ], "u = the glancer.  Finds the jealous partner among tonight's fire-goers (talkers valid this same evening)."),
    eoc("PF_HEART_jealous_one", [
        name_into("pf_jl_cn"),
        {"copy_var": g("pf_jl_a"), "target_var": g("pf_m_other")},
        m("pf_mv_role = 1"), m("pf_m_str_in = pf_jl_str"), {"run_eocs": "PF_MV_jealous"},
        m("pf_jealousy_total = value_or(pf_jealousy_total, 0) + 1"),
    ], "u = the jealous one.  Their view of the glancer takes a jealous half moment."),
]

# ============================================================ GRIEF (mourning, widows, remembrance, burial)
files["grief.json"] = [
    eoc("PF_HEART_grief", [
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_p1", "target_var": ctx("cl_p1"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_p2", "target_var": ctx("cl_p2"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_gd", "target_var": ctx("cl_gd"), "parse_tags": True},
        {"set_string_var": "-", "target_var": g("pf_cl_p1")}, {"set_string_var": "-", "target_var": g("pf_cl_p2")}, {"set_string_var": "-", "target_var": g("pf_cl_gd")},
        {"copy_var": {"var_val": "cl_p1"}, "target_var": g("pf_cl_p1")}, {"copy_var": {"var_val": "cl_p2"}, "target_var": g("pf_cl_p2")},
        {"copy_var": {"var_val": "cl_gd"}, "target_var": g("pf_cl_gd")},
        {"run_eocs": "PF_HEART_child_loss"},
        {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, g("pf_dead_uid")]}]},
         "then": [m("u_pf_mourn_until = time('now') + (value_or(u_pf_rel_stage, 1) >= 3 ? time('14 d') : time('7 d'))"),
                  m("u_pf_has_sweet = 0"), m("u_pf_rel_stage = 0"), m("u_pf_widowed = 1"),
                  {"copy_var": g("pf_dead_uid"), "target_var": {"u_val": "pf_late_sweet"}},
                  {"set_string_var": "none", "target_var": {"u_val": "pf_sweet"}},
                  morale("PF_morale_grief", -25, -40, "7 d", "2 d"),
                  m("pf_widowed_total = value_or(pf_widowed_total, 0) + 1")],
         "else": [{"if": m("pf_read_w >= 40"), "then": [
             m("u_pf_mourn_until = max(value_or(u_pf_mourn_until, 0), time('now') + time('3 d'))"),
             morale("PF_morale_grief", -10, -20, "3 d", "1 d")]}]},
    ], "u = someone who lost a person they cared about (called from PF_GRIEF_one, view of the dead in pf_read_*).  A partner mourns 7 days (a spouse 14) and is widowed; close friends (warmth 40+) mourn 3 days.  Mourners sit apart at the fire and are left out of romance."),
    eoc("PF_HEART_child_loss", [
        m("u_pf_mourn_until = max(value_or(u_pf_mourn_until, 0), time('now') + time('21 d'))"),
        {"u_add_morale": "PF_morale_childloss", "bonus": -40, "max_bonus": -60, "duration": "14 d", "decay_start": "4 d"},
        {"if": "u_is_avatar", "then": [{"u_message": "<global_val:pf_dead_name> is dead.\n\nYou can't stop shaking.  Someone sits with you, and doesn't try to say anything.", "type": "bad", "popup": True}]},
        m("pf_childloss_total = value_or(pf_childloss_total, 0) + 1"),
    ], "u = someone whose child (or a child they took in) just died: the heaviest grief there is (21 days of mourning).",
        condition={"or": [{"compare_string": [g("pf_cl_p1"), {"u_val": "pf_uid"}]}, {"compare_string": [g("pf_cl_p2"), {"u_val": "pf_uid"}]},
                          {"compare_string": [g("pf_cl_gd"), {"u_val": "pf_uid"}]}]}),
    eoc("PF_HEART_avatar_grief", [
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_dead", "target_var": ctx("dref"), "parse_tags": True},
        m("v_dref = 1"),
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_dead_t", "target_var": ctx("dreft"), "parse_tags": True},
        m("v_dreft = time('now')"),
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_p1", "target_var": ctx("cl_p1"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_p2", "target_var": ctx("cl_p2"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_dead_uid>_gd", "target_var": ctx("cl_gd"), "parse_tags": True},
        {"set_string_var": "-", "target_var": g("pf_cl_p1")}, {"set_string_var": "-", "target_var": g("pf_cl_p2")}, {"set_string_var": "-", "target_var": g("pf_cl_gd")},
        {"copy_var": {"var_val": "cl_p1"}, "target_var": g("pf_cl_p1")}, {"copy_var": {"var_val": "cl_p2"}, "target_var": g("pf_cl_p2")},
        {"copy_var": {"var_val": "cl_gd"}, "target_var": g("pf_cl_gd")},
        {"run_eocs": "PF_HEART_child_loss"},
        {"copy_var": g("pf_dead_uid"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_av_grieved = 0"),
        {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, g("pf_dead_uid")]}]},
         "then": [m("pf_av_grieved = 1"), m("u_pf_has_sweet = 0"), m("u_pf_rel_stage = 0"),
                  {"copy_var": g("pf_dead_uid"), "target_var": {"u_val": "pf_late_sweet"}},  # full run: a widower can still raise their children
                  {"set_string_var": "none", "target_var": {"u_val": "pf_sweet"}},
                  morale("PF_morale_grief", -30, -50, "7 d", "2 d"),
                  m("pf_mv_role = 1"), m("pf_m_str_in = 95"), {"run_eocs": "PF_MV_lost_companion"},
                  # full run day 123: Henriette, Dante's wife, died at 09:00 while he waited out the morning; the one line was
                  # buried under a woodland wight's fight and he learned it at the evening's remembrance.  This one can't be missed.
                  {"u_message": "<global_val:pf_dead_name> is dead.\n\nSomething in you goes very quiet.", "type": "bad", "popup": True}],
         "else": [{"if": m("pf_read_w >= 10"), "then": [
             m("pf_av_grieved = 1"),
             m("pf_mv_role = 1"), m("pf_m_str_in = min(95, 50 + pf_read_w / 2)"), {"run_eocs": "PF_MV_lost_companion"},
             {"if": m("pf_read_w >= 50"), "then": [morale("PF_morale_grief", -10, -20, "2 d", "1 d")]}]}]},
    ], "u = you, when someone dies.  If you cared about them you remember losing them (it goes in your journal); losing your partner hurts for a week."),
    eoc("PF_HEART_service", [
        m("pf_fire_service = 1"), m("pf_unmourned = 0"),
        {"copy_var": g("pf_unmourned_name"), "target_var": g("pf_say_b")},
        line("service"),
    ], "u = you.  The first calm evening after a death the fire is for them: everyone's moments tonight are shared mourning (funeral) instead of an ordinary evening, and nobody tells road-trip stories.",
        condition={"and": [m("value_or(pf_unmourned, 0) == 1"), m("time_since(value_or(pf_unmourned_t, 0)) < time('14 d')"), m("pf_fire_n > 0")]}),
    eoc("PF_HEART_burial_signal", [
        {"u_location_variable": g("pf_bur_at"), "terrain": "t_grave_new", "target_max_radius": 3, "true_eocs": ["PF_HEART_burial"]},
    ], "Bottom-up: you finished building something and a fresh grave is right here, within two weeks of a death someone cared about.  That was a burial.",
        condition={"and": ["u_is_avatar", {"compare_string": [ctx("activity"), "ACT_BUILD"]}, m("value_or(pf_unburied, 0) == 1"),
                           m("time_since(value_or(pf_unmourned_t, 0)) < time('14 d')")]},
        eoc_type="EVENT", required_event="character_finished_activity"),
    eoc("PF_HEART_burial", [
        m("pf_unburied = 0"), m("pf_bur_n = 0"),
        {"copy_var": g("pf_unmourned_name"), "target_var": g("pf_say_b")},
        {"u_run_npc_eocs": ["PF_HEART_burial_one"], "local": True, "npc_range": 40},
        {"if": m("pf_bur_n == 0"), "then": [line("burial_alone")]},
        {"if": m("pf_bur_n == 1"), "then": [line("burial_with")]},
        {"if": m("pf_bur_n == 2"), "then": [line("burial_two")]},
        {"if": m("pf_bur_n >= 3"), "then": [line("burial_many")]},
    ], "u = you.  Everyone nearby who cared about the dead comes to the graveside: a shared funeral moment with you, and a day less of mourning."),
    eoc("PF_HEART_burial_one", [
        {"copy_var": g("pf_unmourned_uid"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        {"if": m("pf_read_w >= 10"), "then": [
            {"if": m("pf_bur_n == 0"), "then": [name_into("pf_say_a")]},
            {"if": m("pf_bur_n == 1"), "then": [name_into("pf_bur_n2")]},
            m("pf_bur_n += 1"),
            {"copy_var": g("pf_bur_at"), "target_var": {"u_val": "pf_walk_to"}},
            {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("rand(2) - 1"), "y_adjust": 1},
            {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
            m("u_pf_mourn_until = max(time('now'), value_or(u_pf_mourn_until, 0) - time('1 d'))"),
            {"run_eocs": "PF_MK_funeral", "beta_talker": "avatar"}]},
    ], condition={"not": {"u_has_trait": "PF_CHILD"}}),
]

# ============================================================ OFF-SCREEN COUPLES (band camp)
files["band_hearts.json"] = [
    eoc("PF_HEART_band_viewer", [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_ht_st = value_or(u_pf_rel_stage, 1)"),
        {"if": {"and": [m(ON), {"or": [m("pf_read_x >= 35 + 15 * pf_ht_st"), m("pf_read_a < 25 - 5 * pf_ht_st"), m("pf_read_w < 10")]}]},
         "then": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_bh_from")},
                  {"u_run_npc_eocs": ["PF_HEART_band_dumped"], "unique_ids": [{"u_val": "pf_sweet"}], "local": False},
                  {"copy_var": {"u_val": "pf_sweet"}, "target_var": {"u_val": "pf_ex"}},
                  m("u_pf_has_sweet = 0"), m("u_pf_rel_stage = 0"), {"set_string_var": "none", "target_var": {"u_val": "pf_sweet"}},
                  m("u_pf_awk_until = time('now') + time('5 d')"),
                  m("pf_mv_role = 2"), {"run_eocs": "PF_MV_breakup"},
                  m("pf_breakups_total = value_or(pf_breakups_total, 0) + 1")],
         "else": [{"if": {"and": [m("pf_ht_st == 1"), m("time_since(u_pf_sweet_since) >= time('7 d')"), m("pf_read_w >= 45"), m("pf_read_a >= 45")]},
                   "then": [m("u_pf_rel_stage = 2"), m("u_pf_stage_since = time('now')"),
                            {"u_run_npc_eocs": ["PF_HEART_band_stage"], "unique_ids": [{"u_val": "pf_sweet"}], "local": False}]},
                  {"if": {"and": [m("pf_ht_st == 2"), m("time_since(value_or(u_pf_stage_since, 0)) >= time('14 d')"), m("pf_read_w >= 65"),
                                  m("pf_read_t >= 55"), m("pf_read_a >= 55"), m("value_or(u_pf_commit, 1) != 3"), cooldown_ok_c("u_pf_prop_last", "14 d")]},
                   "then": [m("u_pf_prop_last = time('now')"), {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_bh_from")}, m("pf_bh_yes = 0"),
                            {"u_run_npc_eocs": ["PF_HEART_band_answer"], "unique_ids": [{"u_val": "pf_sweet"}], "local": False},
                            {"if": m("pf_bh_yes == 1"), "then": [m("u_pf_rel_stage = 3"), m("u_pf_stage_since = time('now')"),
                                                               m("pf_mv_role = 2"), m("pf_m_str_in = 85"), {"run_eocs": "PF_MV_wedding"},
                                                               m("pf_weddings_total = value_or(pf_weddings_total, 0) + 1")]}]}]},
    ], "u = an off-screen band member in a relationship, at camp.  The same rules as at the fire, without the lines: couples break up, become partners, propose and marry while you're away.",
        condition={"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"not": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}}]}),
    eoc("PF_HEART_band_dumped", [
        {"copy_var": g("pf_bh_from"), "target_var": {"u_val": "pf_ex"}},
        m("u_pf_has_sweet = 0"), m("u_pf_rel_stage = 0"), {"set_string_var": "none", "target_var": {"u_val": "pf_sweet"}},
        m("u_pf_awk_until = time('now') + time('5 d')"),
        {"copy_var": g("pf_bh_from"), "target_var": g("pf_m_other")}, m("pf_mv_role = 1"), {"run_eocs": "PF_MV_breakup"},
    ], "u = the one who was left (by unique id)."),
    eoc("PF_HEART_band_stage", [m("u_pf_rel_stage = 2"), m("u_pf_stage_since = time('now')")]),
    eoc("PF_HEART_band_answer", [
        {"copy_var": g("pf_bh_from"), "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        m("pf_bh_yes = (pf_read_w >= 60) * (pf_read_a >= 50) * (pf_read_t >= 50) * (value_or(u_pf_commit, 1) != 3)"),
        {"if": m("pf_bh_yes == 1"), "then": [m("u_pf_rel_stage = 3"), m("u_pf_stage_since = time('now')"),
                                           m("pf_mv_role = 1"), m("pf_m_str_in = 85"), {"run_eocs": "PF_MV_wedding"}],
         "else": [m("pf_mv_role = 2"), {"run_eocs": "PF_MV_proposal_declined"}]},
    ], "u = the one proposed to, off-screen."),
]

# ============================================================ JOURNAL (concept §6.2 screen 5: the moments you remember)
JN = 30
JT = [  # (kind, role or None, text)  <global_val:pf_jn_name> is the other person
    ("saved_life", 1, "<global_val:pf_jn_name> saved your life."), ("saved_life", 2, "You saved <global_val:pf_jn_name>'s life."),
    ("care_given", 1, "<global_val:pf_jn_name> looked after you."), ("care_given", 2, "You looked after <global_val:pf_jn_name>."),
    ("shared_danger", None, "You and <global_val:pf_jn_name> fought side by side."),
    ("watch_covered", 1, "<global_val:pf_jn_name> kept watch while you slept."),
    ("near_death", None, "You saw <global_val:pf_jn_name> nearly die."),
    ("gift", 1, "<global_val:pf_jn_name> made you something."), ("gift", 2, "You gave <global_val:pf_jn_name> a gift."),
    ("confession", 1, "<global_val:pf_jn_name> told you how they feel."), ("confession", 2, "You told <global_val:pf_jn_name> how you feel."),
    ("rejected", 1, "<global_val:pf_jn_name> turned you down."), ("rejected", 2, "You turned <global_val:pf_jn_name> down."),
    ("partnered", None, "You and <global_val:pf_jn_name> stopped pretending."),
    ("wedding", 3, "You saw <global_val:pf_jn_name> get married."), ("wedding", None, "You married <global_val:pf_jn_name>."),
    ("breakup", None, "You and <global_val:pf_jn_name> broke up."),
    ("proposal_declined", None, "A proposal, and a 'not yet', with <global_val:pf_jn_name>."),
    ("lost_companion", None, "<global_val:pf_jn_name> died."),
    ("funeral", None, "You and the others mourned <global_val:pf_unmourned_name>."),
    ("birth", None, "<global_val:pf_jn_name> was born."),
    ("adopted", 2, "You took <global_val:pf_jn_name> in."),
    ("taught", 1, "<global_val:pf_jn_name> taught you something."), ("taught", 2, "You taught <global_val:pf_jn_name> something."),
    ("welcomed", None, "<global_val:pf_jn_name> and their people came to live with you."),
    ("secret_kept", 1, "<global_val:pf_jn_name> knows what you are, and kept it to themselves."),
    ("frightened", None, "<global_val:pf_jn_name> saw what you are, and it frightened them."),
    ("ran_off", 1, "<global_val:pf_jn_name> ran when you needed them."), ("ran_off", 2, "You ran, and <global_val:pf_jn_name> was hurt."),
    ("betrayal", 1, "<global_val:pf_jn_name> betrayed you."), ("insult", 1, "<global_val:pf_jn_name> insulted you."),
    ("argument", None, "You and <global_val:pf_jn_name> argued."),
    ("memory_recalled", None, "<global_val:pf_jn_name> brought up an old memory with you."),
    ("voted_for", 1, "<global_val:pf_jn_name> voted for you."), ("voted_for", 2, "You voted for <global_val:pf_jn_name>."),
    ("ruled_for", 1, "<global_val:pf_jn_name> took your side at the meeting."), ("ruled_for", 2, "You ruled for <global_val:pf_jn_name> at the meeting."),
    ("ruled_against", 1, "<global_val:pf_jn_name> ruled against you at the meeting."), ("ruled_against", 2, "You ruled against <global_val:pf_jn_name> at the meeting."),
    ("made_peace", None, "You and <global_val:pf_jn_name> made peace."),
]
jt_eff = [{"set_string_var": "Something happened with <global_val:pf_jn_name>.", "target_var": g("pf_jn_text"), "parse_tags": True}]
for kind, role, text in JT:
    c = [{"compare_string": [g("pf_m_kind"), kind]}]
    if role is not None:
        c.append(m(f"pf_m_role == {role}"))
    jt_eff.append({"if": {"and": c} if len(c) > 1 else c[0], "then": [{"set_string_var": text, "target_var": g("pf_jn_text"), "parse_tags": True}]})
jn_view = []
for k in range(12):
    jn_view += [
        m(f"pf_jn_i = (value_or(pf_jn_count, 0) - 1 - {k} + {JN} * 10) % {JN}"),
        {"set_string_var": "pf_jn_<global_val:pf_jn_i>", "target_var": ctx("jt"), "parse_tags": True},
        {"set_string_var": "pf_jn_t_<global_val:pf_jn_i>", "target_var": ctx("jtt"), "parse_tags": True},
        m(f"pf_jn_ago_{k} = floor((time('now') - value_or(v_jtt, 0)) / time('1 d'))"),
        {"copy_var": {"var_val": "jt"}, "target_var": g("pf_jn_tmp")},
        {"if": m(f"pf_jn_ago_{k} == 0"),
         "then": [{"set_string_var": "<global_val:pf_jn_tmp>  (today)", "target_var": g(f"pf_jn_l_{k}"), "parse_tags": True}],
         "else": [{"set_string_var": f"<global_val:pf_jn_tmp>  (<global_val:pf_jn_ago_{k}> days ago)", "target_var": g(f"pf_jn_l_{k}"), "parse_tags": True}]}]
files["journal.json"] = [
    eoc("PF_JOURNAL_add", [
        m("pf_jn_skip = 0"),
        {"if": {"and": [{"compare_string": [g("pf_m_kind"), "funeral"]}, m("time_since(value_or(pf_jn_fun_t, -1)) >= 0"), m("time_since(value_or(pf_jn_fun_t, -1)) < time('1 h')")]},
         "then": [m("pf_jn_skip = 1")]},
        {"if": {"compare_string": [g("pf_m_kind"), "funeral"]}, "then": [m("pf_jn_fun_t = time('now')")]},
        {"run_eocs": "PF_JOURNAL_write", "condition": m("pf_jn_skip == 0"), "iterations": 1},
    ], "u = you, keeping a memory (called by the spine's PF_MEM_store).  One remembrance is one entry, however many people mourned with you."),
    eoc("PF_JOURNAL_write", [
        m(f"pf_jn_i = value_or(pf_jn_count, 0) % {JN}"),
        {"set_string_var": "someone", "target_var": g("pf_jn_name")},
        {"if": {"not": {"compare_string": [g("pf_m_other"), "none"]}}, "then": regname("pf_m_other", "pf_jn_name")},
    ] + jt_eff + [
        {"set_string_var": "pf_jn_<global_val:pf_jn_i>", "target_var": ctx("jref"), "parse_tags": True},
        {"copy_var": g("pf_jn_text"), "target_var": {"var_val": "jref"}},
        {"set_string_var": "pf_jn_t_<global_val:pf_jn_i>", "target_var": ctx("jtref"), "parse_tags": True},
        m("v_jtref = time('now')"),
        m("pf_jn_count = value_or(pf_jn_count, 0) + 1"),
    ], "u = you, keeping a memory (called by the spine's PF_MEM_store).  Adds a dated line to your journal, a ring of %d entries, written from your side (role-aware)." % JN),
    eoc("PF_JN_open", jn_view + [
        {"if": m("value_or(pf_jn_count, 0) == 0"), "then": [say("Your journal is empty.  The moments people remember will be written here.")],
         "else": [{"run_eoc_selector": [f"PF_JN_pick_{k}" for k in range(12)],
                   "names": [g(f"pf_jn_l_{k}") for k in range(12)],
                   "keys": [c for c in "abcdefghijkl"],
                   "title": "Journal: what you remember (newest first)", "hide_failing": True, "allow_cancel": True}]},
    ], "Journal screen: the newest 12 entries."),
] + [eoc(f"PF_JN_pick_{k}", [{"run_eocs": "PF_JN_open"}], condition=m(f"value_or(pf_jn_count, 0) > {k}")) for k in range(12)]

# ============================================================ WEB (concept §6.2 screen 3: who is with whom, as far as you've seen)
WN = 8
web_desc = [
    {"run_eocs": "PF_ID_ensure"},
    m("pf_wb_me = -1"),
]
for k in range(WN):
    web_desc.append({"if": {"and": [m(f"pf_wb_n > {k}"), {"compare_string": [{"u_val": "pf_uid"}, g(f"pf_wb_u_{k}")]}]}, "then": [m(f"pf_wb_me = {k}")]})
web_desc += [
    name_into("pf_wb_cur"),
    {"if": m("value_or(u_pf_has_sweet, 0) == 1"), "then": [
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_wb_s")}] + regname("pf_wb_s", "pf_wb_sn") + [
        {"if": {"compare_string": [g("pf_wb_s"), "AVATAR"]}, "then": [{"set_string_var": "you", "target_var": g("pf_wb_sn")}]},
        {"switch": m("value_or(u_pf_rel_stage, 1)"), "cases": [
            {"case": 1, "effect": {"set_string_var": "<global_val:pf_wb_cur>: sweet on <global_val:pf_wb_sn>", "target_var": g("pf_wb_cur"), "parse_tags": True}},
            {"case": 2, "effect": {"set_string_var": "<global_val:pf_wb_cur>: with <global_val:pf_wb_sn>", "target_var": g("pf_wb_cur"), "parse_tags": True}},
            {"case": 3, "effect": {"set_string_var": "<global_val:pf_wb_cur>: married to <global_val:pf_wb_sn>", "target_var": g("pf_wb_cur"), "parse_tags": True}}]}]},
    {"if": m("value_or(u_pf_widowed, 0) == 1"), "then": [{"set_string_var": "<global_val:pf_wb_cur> (widowed)", "target_var": g("pf_wb_cur"), "parse_tags": True}]},
    {"if": {"and": [m("has_var(u_pf_mom)"), {"or": [{"compare_string": [{"u_val": "pf_mom"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_dad"}, "AVATAR"]}]}]},
     "then": [{"set_string_var": "<global_val:pf_wb_cur>, your child", "target_var": g("pf_wb_cur"), "parse_tags": True}],
     "else": [{"if": {"and": [m("has_var(u_pf_mom)"), {"not": {"compare_string": [{"u_val": "pf_mom"}, "none"]}}]}, "then": [
         {"copy_var": {"u_val": "pf_mom"}, "target_var": g("pf_wb_s")}] + regname("pf_wb_s", "pf_wb_sn") + [
         {"set_string_var": "<global_val:pf_wb_cur>, <global_val:pf_wb_sn>'s child", "target_var": g("pf_wb_cur"), "parse_tags": True}]}]},
    {"if": {"and": [{"u_has_trait": "PF_CHILD"}, m("has_var(u_pf_guardian)"), {"not": {"compare_string": [{"u_val": "pf_guardian"}, "none"]}}]}, "then": [
        {"copy_var": {"u_val": "pf_guardian"}, "target_var": g("pf_wb_s")}] + regname("pf_wb_s", "pf_wb_sn") + [
        {"if": {"compare_string": [g("pf_wb_s"), "AVATAR"]}, "then": [{"set_string_var": "you", "target_var": g("pf_wb_sn")}]},
        {"set_string_var": "<global_val:pf_wb_cur>, looked after by <global_val:pf_wb_sn>", "target_var": g("pf_wb_cur"), "parse_tags": True}]},
    {"if": {"and": [m("value_or(u_pf_needs_home, 0) == 1")]}, "then": [{"set_string_var": "<global_val:pf_wb_cur>, with nobody to look after them", "target_var": g("pf_wb_cur"), "parse_tags": True}]},
    {"if": m(MOURNING), "then": [{"set_string_var": "<global_val:pf_wb_cur>, grieving", "target_var": g("pf_wb_cur"), "parse_tags": True}]},
    m("pf_wb_bw = 39"), m("pf_wb_bx = 29"), m("pf_wb_bf = -1"), m("pf_wb_br = -1"),
]
for k in range(WN):
    web_desc.append({"if": {"and": [m(f"pf_wb_n > {k}"), m(f"pf_wb_me != {k}"), {"not": {"compare_string": [g(f"pf_wb_u_{k}"), {"u_val": "pf_sweet"}]}}]}, "then": [
        {"copy_var": g(f"pf_wb_u_{k}"), "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
        {"if": m("pf_read_w > pf_wb_bw"), "then": [m("pf_wb_bw = pf_read_w"), m(f"pf_wb_bf = {k}")]},
        {"if": m("pf_read_x > pf_wb_bx"), "then": [m("pf_wb_bx = pf_read_x"), m(f"pf_wb_br = {k}")]}]})
web_desc += [
    {"if": m("pf_wb_bf >= 0"), "then": [
        {"set_string_var": "pf_wb_nm_<global_val:pf_wb_bf>", "target_var": ctx("fn"), "parse_tags": True}, {"copy_var": {"var_val": "fn"}, "target_var": g("pf_wb_tmp")},
        {"set_string_var": "<global_val:pf_wb_cur>; close to <global_val:pf_wb_tmp>", "target_var": g("pf_wb_cur"), "parse_tags": True}]},
    {"if": m("pf_wb_br >= 0"), "then": [
        {"set_string_var": "pf_wb_nm_<global_val:pf_wb_br>", "target_var": ctx("rn"), "parse_tags": True}, {"copy_var": {"var_val": "rn"}, "target_var": g("pf_wb_tmp")},
        {"set_string_var": "<global_val:pf_wb_cur>; at odds with <global_val:pf_wb_tmp>", "target_var": g("pf_wb_cur"), "parse_tags": True}]},
    {"if": m("pf_wb_me >= 0"), "then": [
        {"set_string_var": "pf_wb_l_<global_val:pf_wb_me>", "target_var": ctx("lref"), "parse_tags": True},
        {"copy_var": g("pf_wb_cur"), "target_var": {"var_val": "lref"}}]},
]
files["web.json"] = [
    eoc("PF_WEB_open", [
        m("pf_wb_n = 0"),
        {"u_run_npc_eocs": ["PF_WEB_collect"], "local": True, "npc_range": 40},
        {"u_run_npc_eocs": ["PF_WEB_describe"], "local": True, "npc_range": 40},
        {"if": m("pf_wb_n == 0"), "then": [say("Nobody around to tell you about.")],
         "else": [{"run_eoc_selector": [f"PF_WEB_pick_{k}" for k in range(WN)],
                   "names": [g(f"pf_wb_l_{k}") for k in range(WN)],
                   "keys": [c for c in "abcdefgh"],
                   "title": "Who is with whom (what you've seen around you)", "hide_failing": True, "allow_cancel": True}]},
    ], "Web screen: for each adult around you, who they're with, who they're closest to, and who they're at odds with (among the people here)."),
    eoc("PF_WEB_collect", [
        {"run_eocs": "PF_ID_ensure"},
        {"set_string_var": "pf_wb_u_<global_val:pf_wb_n>", "target_var": ctx("uref"), "parse_tags": True},
        {"copy_var": {"u_val": "pf_uid"}, "target_var": {"var_val": "uref"}},
        {"set_string_var": "pf_wb_nm_<global_val:pf_wb_n>", "target_var": ctx("nref"), "parse_tags": True},
        {"set_string_var": "<u_name>", "target_var": {"var_val": "nref"}, "parse_tags": True},
        m("pf_wb_n += 1"),
    ], condition=m(f"pf_wb_n < {WN}")),
    eoc("PF_WEB_describe", web_desc, "u = one of the people collected.  Builds their line from their own views."),
] + [eoc(f"PF_WEB_pick_{k}", [{"run_eocs": "PF_WEB_open"}], condition=m(f"pf_wb_n > {k}")) for k in range(WN)]


def compass(dx, dy, out):
    """Effects: a compass word (north, southeast...) for an offset, into global `out` (y grows southward)."""
    return [{"set_string_var": "", "target_var": g(out + "_ns")}, {"set_string_var": "", "target_var": g(out + "_ew")},
            {"if": m(f"abs({dy}) * 2 >= abs({dx})"), "then": [
                {"if": m(f"{dy} < 0"), "then": [{"set_string_var": "north", "target_var": g(out + "_ns")}],
                 "else": [{"set_string_var": "south", "target_var": g(out + "_ns")}]}]},
            {"if": m(f"abs({dx}) * 2 >= abs({dy})"), "then": [
                {"if": m(f"{dx} < 0"), "then": [{"set_string_var": "west", "target_var": g(out + "_ew")}],
                 "else": [{"set_string_var": "east", "target_var": g(out + "_ew")}]}]},
            {"set_string_var": f"<global_val:{out}_ns><global_val:{out}_ew>", "target_var": g(out), "parse_tags": True}]


# ============================================================ EVENTS & ANNIVERSARIES (memories come back on the date)
EV = 20
an_eff = [m("pf_an_done = 0")]
for k in range(EV):
    an_eff.append({"if": {"and": [m("pf_an_done == 0"), m(f"value_or(pf_ev_n, 0) > {k}")]}, "then": [
        m(f"pf_an_d = floor((time('now') - value_or(pf_ev_{k}_t, 0)) / time('1 d'))"),
        m("pf_an_m = (pf_an_d >= 30) * (pf_an_d < 33) * 30 + (pf_an_d >= 90) * (pf_an_d < 93) * 90 + (pf_an_d >= 364) * (pf_an_d < 367) * 364"),
        {"if": {"and": [m("pf_an_m > 0"),
                        m(f"(pf_an_m == 30) * value_or(pf_ev_{k}_m30, 0) + (pf_an_m == 90) * value_or(pf_ev_{k}_m90, 0) + (pf_an_m == 364) * value_or(pf_ev_{k}_m364, 0) == 0")]},
         "then": [m("pf_an_done = 1"),
                  m(f"pf_ev_{k}_m30 = (pf_an_m == 30) ? 1 : value_or(pf_ev_{k}_m30, 0)"),
                  m(f"pf_ev_{k}_m90 = (pf_an_m == 90) ? 1 : value_or(pf_ev_{k}_m90, 0)"),
                  m(f"pf_ev_{k}_m364 = (pf_an_m == 364) ? 1 : value_or(pf_ev_{k}_m364, 0)"),
                  {"set_string_var": "a month", "target_var": g("pf_an_words")},
                  {"if": m("pf_an_m == 90"), "then": [{"set_string_var": "three months", "target_var": g("pf_an_words")}]},
                  {"if": m("pf_an_m == 364"), "then": [{"set_string_var": "a year", "target_var": g("pf_an_words")}]},
                  {"copy_var": g(f"pf_ev_{k}_name"), "target_var": g("pf_an_name")},
                  {"copy_var": g(f"pf_ev_{k}_youname"), "target_var": g("pf_an_youname")},
                  # full run day 152: "Gattsu Riley is a month old today.  Somebody makes a fuss of it." (died day 124)
                  # full run day 181: "Marylin Whitmore is a month old today." for a five-year-old (Growing up: fast).  Birth
                  # dates count in real days; at a faster pace, only the accelerated month mark (a year old) is said.
                  {"if": {"compare_string": [g(f"pf_ev_{k}_kind"), "birth"]}, "then": [
                      {"if": m("value_or(pf_set_grow, 1) == 1"), "then": [
                          {"if": m("pf_an_m == 30"), "then": [{"set_string_var": "a year", "target_var": g("pf_an_words")}],
                           "else": [m("pf_an_m = -1")]}]},
                      {"if": m("value_or(pf_set_grow, 1) == 2"), "then": [m("pf_an_m = -1")]},
                      {"if": m("pf_an_m > 0"), "then": [
                          {"run_eocs": "PF_HEART_an_gone"},
                          {"if": m("pf_an_gone == 1"), "then": [line("anniv_birth_gone")], "else": [line("anniv_birth")]}]}]},
                  {"if": {"compare_string": [g(f"pf_ev_{k}_kind"), "death"]}, "then": [line("anniv_death")],
                   "else": [{"if": {"compare_string": [g(f"pf_ev_{k}_kind"), "birth"]}, "then": []},
                            {"if": {"and": [m(f"value_or(pf_ev_{k}_you, 0) == 1"), {"compare_string": [g(f"pf_ev_{k}_kind"), "wed"]}]},
                             # full run day 143: "since you married Henriette Nguyen.  They remembered." 20 days after she died
                             "then": [{"set_string_var": "pf_name_<u_val:pf_sweet>", "target_var": ctx("swn"), "parse_tags": True},
                                      {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"var_val": "swn"}, g("pf_an_youname")]}]},
                                       "then": [line("anniv_wed_you"), {"run_eocs": "PF_HEART_together", "alpha_talker": "avatar"}],
                                       "else": [line("anniv_wed_lost")]}],
                             "else": [{"if": {"compare_string": [g(f"pf_ev_{k}_kind"), "wed"]}, "then": [line("anniv_wed")]}]}]}]}]})
def evname(field, ctxn):
    return {"set_string_var": "pf_ev_<global_val:pf_ev_i>_" + field, "target_var": ctx(ctxn), "parse_tags": True}
ev_add = [
    m(f"pf_ev_i = value_or(pf_ev_n, 0) % {EV}"),
    evname("kind", "ek"), {"copy_var": g("pf_ev_new_kind"), "target_var": {"var_val": "ek"}},
    evname("name", "en"), {"copy_var": g("pf_ev_new_name"), "target_var": {"var_val": "en"}},
    evname("youname", "ey"), {"copy_var": g("pf_ev_new_youname"), "target_var": {"var_val": "ey"}},
    evname("you", "eu"), m("v_eu = value_or(pf_ev_new_you, 0)"),
    evname("t", "et"), m("v_et = time('now')"),
    evname("m30", "e1"), m("v_e1 = 0"), evname("m90", "e2"), m("v_e2 = 0"), evname("m364", "e3"), m("v_e3 = 0"),
    m("pf_ev_n = value_or(pf_ev_n, 0) + 1"),
]
files["events.json"] = [
    eoc("PF_HEART_event_add", ev_add, "Records a dated event (pf_ev_new_kind: death or wed; pf_ev_new_name; pf_ev_new_you/youname) in a ring of 20, for anniversaries."),
    eoc("PF_HEART_event_death", [
        {"set_string_var": "death", "target_var": g("pf_ev_new_kind")},
        {"copy_var": g("pf_dead_name"), "target_var": g("pf_ev_new_name")},
        m("pf_ev_new_you = 0"), {"set_string_var": "nobody", "target_var": g("pf_ev_new_youname")},
        {"run_eocs": "PF_HEART_event_add"},
    ], "A death someone grieved becomes an event to remember."),
    eoc("PF_HEART_an_gone", [m("pf_an_gone = 0")] + [
        {"if": {"and": [m(f"value_or(pf_ev_n, 0) > {k}"), {"compare_string": [g(f"pf_ev_{k}_kind"), "death"]},
                        {"compare_string": [g(f"pf_ev_{k}_name"), g("pf_an_name")]}]}, "then": [m("pf_an_gone = 1")]} for k in range(EV)],
        "Is the child whose birthday it is (pf_an_name) among the dead in the event log?  pf_an_gone 1 if so."),
    eoc("PF_HEART_anniv", an_eff,
        "u = you, at the fire.  A month, three months and a year after a death or a wedding (within three days of the date, once each), it comes back: one anniversary per evening."),
    eoc("PF_HEART_together", [
        {"if": m("value_or(u_pf_rel_stage, 1) >= 3"), "then": [{"u_add_morale": "PF_morale_together", "bonus": 10, "max_bonus": 20, "duration": "12 h", "decay_start": "6 h"}],
         "else": [{"u_add_morale": "PF_morale_together", "bonus": 6, "max_bonus": 12, "duration": "12 h", "decay_start": "6 h"}]},
    ], "u = you.  Time with the one you're with lifts your mood (more when married)."),
    eoc("PF_HEART_partner_scare", [
        m("pf_scare_last = time('now')"),
        {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")},
        {"run_eocs": "PF_FIND_by_uid"},
        {"u_location_variable": g("pf_scare_av")},
        {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_HEART_scare_one", "alpha_talker": g("pf_find_who"), "beta_talker": "avatar"}]},
    ], "u = you, nearly killed.  If the one you're with is close, they're at your side.",
        condition={"and": [m("value_or(u_pf_has_sweet, 0) == 1"), cooldown_ok_c("pf_scare_last", "1 h")]}),
    eoc("PF_HEART_scare_one", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_scare_av) <= 15"), "then": [
            name_into("pf_say_a"), line("scare"),
            m("pf_m_str_in = 60"), {"run_eocs": "PF_MK_care_given"}]},
    ], "Alpha = your partner (found this turn), beta = you."),
]

# ============================================================ KNOWN PEOPLE (concept §6.2 screen 5b: everyone you've met)
KN = 20
# full run day 103: the screen showed the first 20 people you'd met, so once you knew more than 20 the newest (the band
# you were courting) never appeared, while the dead kept their places.  Now the living come first (first met first),
# then the dead, up to 20 rows.  pf_kn_ix_<row> remembers which known-list entry each row is.
kn_scan = [
    {"set_string_var": "u_pf_known_<global_val:pf_kn_i>", "target_var": ctx("kr"), "parse_tags": True},
    {"copy_var": {"var_val": "kr"}, "target_var": g("pf_kn_uid")},
    {"set_string_var": "pf_reg_<global_val:pf_kn_uid>_dead", "target_var": ctx("kd"), "parse_tags": True},
    {"if": m("(value_or(v_kd, 0) == 1) == (pf_kn_pass == 2)"), "then": regname("pf_kn_uid", "pf_kn_name") + [
        {"if": {"compare_string": [g("pf_kn_name"), ""]}, "then": [{"set_string_var": "someone you met", "target_var": g("pf_kn_name")}]},
        {"set_string_var": "pf_kn_l_<global_val:pf_kn_s>", "target_var": ctx("kt"), "parse_tags": True},
        {"set_string_var": "pf_kn_ix_<global_val:pf_kn_s>", "target_var": ctx("kx"), "parse_tags": True},
        m("v_kx = pf_kn_i"),
        {"if": m("pf_kn_pass == 2"),
         "then": [{"set_string_var": "<global_val:pf_kn_name>  (gone)", "target_var": {"var_val": "kt"}, "parse_tags": True}],
         "else": [
            {"copy_var": g("pf_kn_uid"), "target_var": g("pf_m_other")},
            {"run_eocs": "PF_VIEW_read"},
            {"set_string_var": "pf_kn_l_<global_val:pf_kn_s>", "target_var": ctx("kt"), "parse_tags": True},
            {"set_string_var": "u_pf_v_<global_val:pf_kn_uid>_l", "target_var": ctx("kl"), "parse_tags": True},
            # calendar days (full run: "saw them today" at 06:00 for someone last seen the afternoon before)
            m("pf_kn_days = floor(time('now') / time('1 d')) - floor(value_or(v_kl, time('now')) / time('1 d'))"),
            {"if": m("pf_kn_days == 0"),
             "then": [{"set_string_var": "<global_val:pf_kn_name>: <global_val:pf_read_tier_name>, saw them today", "target_var": {"var_val": "kt"}, "parse_tags": True}],
             "else": [{"if": m("pf_kn_days == 1"), "then": [{"set_string_var": "<global_val:pf_kn_name>: <global_val:pf_read_tier_name>, a day since anything happened", "target_var": {"var_val": "kt"}, "parse_tags": True}],
                       "else": [{"set_string_var": "<global_val:pf_kn_name>: <global_val:pf_read_tier_name>, <global_val:pf_kn_days> days since anything happened", "target_var": {"var_val": "kt"}, "parse_tags": True}]}]}]},
        m("pf_kn_s += 1")]},
    m("pf_kn_i += pf_kn_di"),
]
# full run day 123: with 20 living people known, Hubert Hughes (killed in the siege that night) and Isaias didn't show at all.
# Up to 4 rows are kept for the dead, newest first (the end of the known list).
kn_count = [{"set_string_var": "u_pf_known_<global_val:pf_kn_i>", "target_var": ctx("kr"), "parse_tags": True},
            {"copy_var": {"var_val": "kr"}, "target_var": g("pf_kn_uid")},
            {"set_string_var": "pf_reg_<global_val:pf_kn_uid>_dead", "target_var": ctx("kd"), "parse_tags": True},
            {"if": m("value_or(v_kd, 0) == 1"), "then": [m("pf_kn_dn += 1")]}, m("pf_kn_i += 1")]
kn_eff = [m("pf_kn_stamp = value_or(pf_kn_stamp, 0) + 1"), m("pf_kn_i = 0"), m("pf_kn_dn = 0"),
          {"run_eocs": "PF_KNOWN_count_one", "condition": m("pf_kn_i < value_or(u_pf_known_n, 0)"), "iterations": 120},
          m(f"pf_kn_lim = {KN} - min(pf_kn_dn, 4)"),
          m("pf_kn_i = 0"), m("pf_kn_s = 0"), m("pf_kn_pass = 1"), m("pf_kn_di = 1"),
          {"run_eocs": "PF_KNOWN_scan_one", "condition": {"and": [m("pf_kn_s < pf_kn_lim"), m("pf_kn_i < value_or(u_pf_known_n, 0)")]}, "iterations": 120},
          m("pf_kn_j = 0"), {"run_eocs": "PF_KNOWN_backfill_one", "condition": m("pf_kn_j < value_or(u_pf_known_n, 0)"), "iterations": 120},
          m("pf_kn_pass = 2"), m("pf_kn_di = 0"), m("pf_kn_dshown = 0"),
          {"run_eocs": "PF_KNOWN_dead_next", "condition": {"and": [m(f"pf_kn_s < {KN}"), m("pf_kn_dshown < pf_kn_dn")]}, "iterations": 20}]
# full run day 125: "newest first" went by when you met them, so Henriette (met early, died last) had no row.  Each dead row
# is the most recent death not yet shown (pf_reg_<uid>_dead_t; deaths from before it was kept count as oldest).
kn_dead_pick = [{"set_string_var": "u_pf_known_<global_val:pf_kn_j>", "target_var": ctx("kr"), "parse_tags": True},
                {"copy_var": {"var_val": "kr"}, "target_var": g("pf_kn_ju")},
                {"set_string_var": "pf_reg_<global_val:pf_kn_ju>_dead", "target_var": ctx("kd"), "parse_tags": True},
                {"set_string_var": "pf_reg_<global_val:pf_kn_ju>_dead_t", "target_var": ctx("kdt"), "parse_tags": True},
                {"set_string_var": "pf_kn_shown_<global_val:pf_kn_j>", "target_var": ctx("ksh"), "parse_tags": True},
                {"if": {"and": [m("value_or(v_kd, 0) == 1"), m("value_or(v_ksh, -1) != pf_kn_stamp"), m("value_or(v_kdt, 0) + pf_kn_j * 0.001 > pf_kn_best")]},
                 "then": [m("pf_kn_best = value_or(v_kdt, 0) + pf_kn_j * 0.001"), m("pf_kn_bi = pf_kn_j")]},
                m("pf_kn_j += 1")]
files["known.json"] = [
    eoc("PF_KNOWN_count_one", kn_count, "u = you.  Counts the dead in your known list (pf_kn_dn)."),
    # deaths from before pf_reg_<uid>_dead_t existed: take the time from a journal death event with the same name
    eoc("PF_KNOWN_backfill_one", [
        {"set_string_var": "u_pf_known_<global_val:pf_kn_j>", "target_var": ctx("kr"), "parse_tags": True},
        {"copy_var": {"var_val": "kr"}, "target_var": g("pf_kn_ju")},
        {"set_string_var": "pf_reg_<global_val:pf_kn_ju>_dead", "target_var": ctx("kd"), "parse_tags": True},
        {"set_string_var": "pf_reg_<global_val:pf_kn_ju>_dead_t", "target_var": ctx("kdt"), "parse_tags": True},
        {"if": {"and": [m("value_or(v_kd, 0) == 1"), m("has_var(v_kdt) == 0")]}, "then": regname("pf_kn_ju", "pf_kn_bfname") + [
            m("v_kdt = 0")] + [
            {"if": {"and": [{"compare_string": [g(f"pf_ev_{e}_kind"), "death"]}, {"compare_string": [g(f"pf_ev_{e}_name"), g("pf_kn_bfname")]}]},
             "then": [m(f"v_kdt = pf_ev_{e}_t")]} for e in range(EV)]},
        m("pf_kn_j += 1"),
    ], "u = you.  Gives a dead known person a time of death from the journal, once."),
    eoc("PF_KNOWN_dead_pick", kn_dead_pick, "u = you.  One step of finding the most recent death not yet listed."),
    eoc("PF_KNOWN_dead_next", [
        m("pf_kn_best = -1"), m("pf_kn_bi = -1"), m("pf_kn_j = 0"),
        {"run_eocs": "PF_KNOWN_dead_pick", "condition": m("pf_kn_j < value_or(u_pf_known_n, 0)"), "iterations": 120},
        m("pf_kn_dshown += 1"),
        {"if": m("pf_kn_bi >= 0"), "then": [
            {"set_string_var": "pf_kn_shown_<global_val:pf_kn_bi>", "target_var": ctx("ksh"), "parse_tags": True}, m("v_ksh = pf_kn_stamp"),
            m("pf_kn_i = pf_kn_bi"), {"run_eocs": "PF_KNOWN_scan_one"}]},
    ], "u = you.  Lists the most recent death not yet listed (one row)."),
    eoc("PF_KNOWN_scan_one", kn_scan, "u = you.  One step of the People you know scan: entry pf_kn_i of your known list, living on pass 1 (forward), the dead on pass 2 (backward, newest first)."),
    eoc("PF_KNOWN_open", [{"run_eocs": "PF_ID_ensure"}] + kn_eff + [
        m("pf_kn_heard_n = min(value_or(pf_rumors_n, 0), 6)"),
        {"set_string_var": "Heard of: <global_val:pf_kn_heard_n> groups out there (rumors)", "target_var": g("pf_kn_heard"), "parse_tags": True},
        {"if": {"and": [m("value_or(u_pf_known_n, 0) == 0"), m("pf_kn_heard_n == 0")]}, "then": [say("You don't really know anyone yet.")],
         "else": [{"run_eoc_selector": ["PF_KNOWN_heard"] + [f"PF_KNOWN_pick_{k}" for k in range(KN)],
                   "names": [g("pf_kn_heard")] + [g(f"pf_kn_l_{k}") for k in range(KN)],
                   "keys": ["0"] + [c for c in "abcdefghijklmnopqrst"],
                   "title": "People you know (first met first; the gone last, newest first)", "hide_failing": True, "allow_cancel": True}]},
    ], "u = you.  Everyone you know: how you see them, how long since anything happened between you, and who is gone."),
    # full run day 78: courting a band meant the overmap, its hover names, the V list and three trips, because nothing said
    # where someone you know had gone.  Every 10 minutes, anyone of ours you can actually see is "last seen" there.
    eoc("PF_SEEN_tick", [
        {"u_location_variable": g("pf_seen_av")},
        {"u_run_npc_eocs": ["PF_SEEN_one"], "local": True, "npc_range": 40},
    ], "u = you.  Records where and when you last saw each person (pf_seen_<uid>, pf_seen_<uid>_t).",
        recurrence="10 minutes", **{"global": True}, condition={"not": {"u_has_effect": "sleep"}}),
    eoc("PF_SEEN_one", [
        {"u_location_variable": g("pf_seen_pos")},
        {"if": {"line_of_sight": 40, "loc_1": g("pf_seen_av"), "loc_2": g("pf_seen_pos")}, "then": [
            {"set_string_var": "pf_seen_<u_val:pf_uid>", "target_var": ctx("sn"), "parse_tags": True},
            {"copy_var": g("pf_seen_pos"), "target_var": {"var_val": "sn"}},
            {"set_string_var": "pf_seen_<u_val:pf_uid>_t", "target_var": ctx("st"), "parse_tags": True},
            m("v_st = time('now')")]},
    ], condition=m("has_var(u_pf_uid)")),
    eoc("PF_KNOWN_band_read", [
        m("pf_kb_ok = 1"), {"copy_var": {"u_val": "pf_vpos"}, "target_var": g("pf_kb_v")},
        m("pf_kb_camp = value_or(u_pf_camp_until, 0) > time('now')"),  # 2026-10-17: bands make camp (gen_home drift, gen_people PF_WHERE)
        {"if": m("has_var(u_pf_goal)"), "then": [{"copy_var": {"u_val": "pf_goal"}, "target_var": g("pf_kb_g")}, m("pf_kb_hg = 1")],
         "else": [m("pf_kb_hg = 0")]},
    ], "u = a band leader (reached by unique id).  The band's position (vpos, its leader's body while on-screen) and goal for word along the road."),
    eoc("PF_KNOWN_where", regname("pf_kn_uid", "pf_kn_name") + [
        # Kinfold day 136: Janey was on the People list at 33 tiles (her camp, behind walls), but "You last saw Janey Hammond
        # 11 steps southwest of here, 10 days ago".  Anyone nearby right now (loaded, within 60) is where they are now.
        {"u_location_variable": g("pf_seen_av")},
        {"u_run_npc_eocs": [{"id": "PF_KNOWN_where_live", "condition": {"compare_string": [{"u_val": "pf_uid"}, g("pf_kn_uid")]}, "effect": [
            {"u_location_variable": g("pf_seen_pos")},
            {"set_string_var": "pf_seen_<u_val:pf_uid>", "target_var": ctx("sn"), "parse_tags": True},
            {"copy_var": g("pf_seen_pos"), "target_var": {"var_val": "sn"}},
            {"set_string_var": "pf_seen_<u_val:pf_uid>_t", "target_var": ctx("st"), "parse_tags": True},
            m("v_st = time('now')")]}], "local": True, "npc_range": 60},
        {"if": {"compare_string": [g("pf_kn_name"), ""]}, "then": [{"set_string_var": "someone you met", "target_var": g("pf_kn_name")}]},
        {"set_string_var": "pf_reg_<global_val:pf_kn_uid>_dead", "target_var": ctx("kd"), "parse_tags": True},
        {"set_string_var": "pf_seen_<global_val:pf_kn_uid>_t", "target_var": ctx("st"), "parse_tags": True},
        {"set_string_var": "pf_seen_<global_val:pf_kn_uid>", "target_var": ctx("sn"), "parse_tags": True},
        {"if": m("value_or(v_kd, 0) == 1"), "then": [say("<global_val:pf_kn_name> is gone.")],
         "else": [{"if": m("value_or(v_st, -1) < 0"), "then": [say("You haven't kept track of where <global_val:pf_kn_name> went.")],
                   "else": [
            {"copy_var": {"var_val": "sn"}, "target_var": g("pf_kn_seen")},
            {"u_location_variable": g("pf_kn_av")},
            m("pf_kn_dx = pf_kn_seen.x - pf_kn_av.x"), m("pf_kn_dy = pf_kn_seen.y - pf_kn_av.y"),
            m("pf_kn_d = max(abs(pf_kn_dx), abs(pf_kn_dy))"),
            m("pf_kn_mt = floor((pf_kn_d + 12) / 24)"),
            m("pf_kn_h = floor((time('now') - v_st) / time('1 h'))"), m("pf_kn_dd = floor(pf_kn_h / 24)"),
            # compass: y grows southward; a direction is "straight" when one axis is more than twice the other
            {"set_string_var": "", "target_var": g("pf_kn_ns")}, {"set_string_var": "", "target_var": g("pf_kn_ew")},
            {"if": m("abs(pf_kn_dy) * 2 >= abs(pf_kn_dx)"), "then": [
                {"if": m("pf_kn_dy < 0"), "then": [{"set_string_var": "north", "target_var": g("pf_kn_ns")}],
                 "else": [{"set_string_var": "south", "target_var": g("pf_kn_ns")}]}]},
            {"if": m("abs(pf_kn_dx) * 2 >= abs(pf_kn_dy)"), "then": [
                {"if": m("pf_kn_dx < 0"), "then": [{"set_string_var": "west", "target_var": g("pf_kn_ew")}],
                 "else": [{"set_string_var": "east", "target_var": g("pf_kn_ew")}]}]},
            {"set_string_var": "<global_val:pf_kn_ns><global_val:pf_kn_ew>", "target_var": g("pf_kn_dir"), "parse_tags": True},
            {"if": m("pf_kn_d < 4"), "then": [{"set_string_var": "right about here", "target_var": g("pf_kn_where")}],
             "else": [{"if": m("pf_kn_d < 48"),
                       "then": [{"set_string_var": "<global_val:pf_kn_d> steps <global_val:pf_kn_dir> of here", "target_var": g("pf_kn_where"), "parse_tags": True}],
                       "else": [{"set_string_var": "about <global_val:pf_kn_mt> map tiles <global_val:pf_kn_dir> of here", "target_var": g("pf_kn_where"), "parse_tags": True}]}]},
            {"if": m("pf_kn_h < 1"), "then": [{"set_string_var": "within the hour", "target_var": g("pf_kn_when")}],
             "else": [{"if": m("pf_kn_h < 24"),
                       "then": [{"set_string_var": "<global_val:pf_kn_h> hours ago", "target_var": g("pf_kn_when"), "parse_tags": True}],
                       "else": [{"if": m("pf_kn_dd == 1"), "then": [{"set_string_var": "a day ago", "target_var": g("pf_kn_when")}],
                                 "else": [{"set_string_var": "<global_val:pf_kn_dd> days ago", "target_var": g("pf_kn_when"), "parse_tags": True}]}]}]},
            say("You last saw <global_val:pf_kn_name> <global_val:pf_kn_where>, <global_val:pf_kn_when>.")]}]},
        # full run day 150: Golly Whitmore's band was 250 tiles east while the overmap showed them (their parked bodies) 3 tiles
        # north, and "last seen" was 6 days old; Dante walked to an empty forest.  Bands talk to bands: for someone who travels
        # with a band that's off-screen, word along the road says where the band really is and where it's heading.
        # day 151: Consuelo's band was 3 map tiles off and in range (online), so "word along the road" stayed silent, and Dante
        # made three trips.  An online band's vpos follows its leader's body, so it answers then too; and a member is asked
        # through their leader (the leader's vpos is the band's).  One off-screen talker at a time: two lookups in a row.
        m("pf_kb_ok = 0"), m("pf_kb_lead = 0"),
        {"u_run_npc_eocs": [{"id": "PF_KNOWN_band_pos", "effect": [
            {"if": m("(value_or(u_pf_band, 0) > 0) * (value_or(u_pf_resident, 0) == 0)"), "then": [
                {"if": m("(value_or(u_pf_is_leader, 0) == 1) * has_var(u_pf_vpos)"), "then": [{"run_eocs": "PF_KNOWN_band_read"}],
                 "else": [{"if": m("has_var(u_pf_leader)"), "then": [{"copy_var": {"u_val": "pf_leader"}, "target_var": g("pf_kb_leader")}, m("pf_kb_lead = 1")]}]}]}]}],
         "unique_ids": [g("pf_kn_uid")], "local": False},
        {"if": m("(pf_kb_ok == 0) * (pf_kb_lead == 1)"), "then": [
            {"u_run_npc_eocs": [{"id": "PF_KNOWN_band_lead", "condition": m("(value_or(u_pf_is_leader, 0) == 1) * has_var(u_pf_vpos)"),
                                 "effect": [{"run_eocs": "PF_KNOWN_band_read"}]}],
             "unique_ids": [g("pf_kb_leader")], "local": False}]},
        {"if": m("pf_kb_ok == 1"), "then": [
            {"u_location_variable": g("pf_kb_av")},
            m("pf_kb_dx = pf_kb_v.x - pf_kb_av.x"), m("pf_kb_dy = pf_kb_v.y - pf_kb_av.y"),
            m("pf_kb_mt = floor((max(abs(pf_kb_dx), abs(pf_kb_dy)) + 12) / 24)")] + compass("pf_kb_dx", "pf_kb_dy", "pf_kb_dir") + [
            {"if": m("pf_kb_hg == 1"), "then": [
                m("pf_kb_hx = pf_kb_g.x - pf_kb_v.x"), m("pf_kb_hy = pf_kb_g.y - pf_kb_v.y")] + compass("pf_kb_hx", "pf_kb_hy", "pf_kb_head") + [
                {"if": m("max(abs(pf_kb_hx), abs(pf_kb_hy)) < 12"), "then": [{"set_string_var": "settling there", "target_var": g("pf_kb_heading")}],
                 "else": [{"set_string_var": "heading <global_val:pf_kb_head>", "target_var": g("pf_kb_heading"), "parse_tags": True}]}],
             "else": [{"set_string_var": "staying put", "target_var": g("pf_kb_heading")}]},
            {"if": m("value_or(pf_kb_camp, 0) == 1"), "then": [{"set_string_var": "camped there for a while", "target_var": g("pf_kb_heading")}]},
            {"if": m("pf_kb_mt < 2"), "then": [say("Word along the road puts <global_val:pf_kn_name>'s people close by, <global_val:pf_kb_heading>.")],
             "else": [say("Word along the road puts <global_val:pf_kn_name>'s people about <global_val:pf_kb_mt> map tiles <global_val:pf_kb_dir> of here, <global_val:pf_kb_heading>.")]}]},
    ], "u = you, pf_kn_uid = someone you know.  Where you last saw them, from where you stand now; and for someone with a band out of sight, where the band really is (A-Life data)."),
] + [eoc(f"PF_KNOWN_pick_{k}", [{"set_string_var": f"u_pf_known_<global_val:pf_kn_ix_{k}>", "target_var": ctx("kr"), "parse_tags": True},
                                    {"copy_var": {"var_val": "kr"}, "target_var": g("pf_kn_uid")}, {"run_eocs": "PF_KNOWN_where"}],
         condition=m(f"value_or(pf_kn_s, 0) > {k}")) for k in range(KN)] + [
    eoc("PF_KNOWN_heard", [{"run_eocs": "PF_HOME_rumors"}], "People you know: the groups you've only heard of (v0.4 rumors, newest first).",
        condition=m("value_or(pf_rumors_n, 0) > 0"))]

# ============================================================ LINES
LINES = {
    "partner_npc": ("<global_val:pf_say_a> and <global_val:pf_say_b> have stopped pretending they're just friends.", "info"),
    "partner_you": ("<global_val:pf_say_a> moves their bedroll next to yours tonight, and doesn't say anything about it.", "good"),
    "engaged_npc": ("<global_val:pf_say_a> asks <global_val:pf_say_b> to marry them, right there in front of everyone.  <global_val:pf_say_b> says yes, and the whole camp cheers.  The wedding will be its own night.", "good"),
    "engaged_you": ("You say yes.  <global_val:pf_say_a> can't stop grinning.  The wedding will be the first quiet evening after tomorrow.", "good"),
    "wedding_npc": ("Tonight is a wedding.  <global_val:pf_say_a> and <global_val:pf_say_b> stand by the fire while everyone gathers close, and with all of them as witnesses, they're married.", "good",
                    "Tonight is a wedding.  <global_val:pf_say_a> and <global_val:pf_say_b> stand in the middle of the room while everyone crowds in close, and with all of them as witnesses, they're married."),
    "wedding_you": ("Tonight is your wedding.  Everyone gathers close as <global_val:pf_say_a> takes your hands by the fire, and with all of them as witnesses, you're married.", "good",
                    "Tonight is your wedding.  Everyone crowds into the room as <global_val:pf_say_a> takes your hands, and with all of them as witnesses, you're married."),
    "wedding_feast": ("Someone produces a bottle they'd been saving, and for one night nobody talks about the dead.", "good"),
    "burial_two":  ("You bury <global_val:pf_say_b>.  <global_val:pf_say_a> and <global_val:pf_bur_n2> stand with you at the graveside.", "info"),
    "burial_many": ("You bury <global_val:pf_say_b>.  <global_val:pf_say_a>, <global_val:pf_bur_n2> and the others stand with you at the graveside, and nobody hurries.", "info"),
    "anniv_death": ("It's been <global_val:pf_an_words> since <global_val:pf_an_name> died.  Someone pours a little out for them, and nobody says anything for a while.", "info"),
    "anniv_wed":   ("<global_val:pf_an_name> have been married <global_val:pf_an_words> today.  Somebody finds a bottle.", "good"),
    "anniv_wed_you": ("It's been <global_val:pf_an_words> since you married <global_val:pf_an_youname>.  They remembered.", "good"),
    "anniv_wed_lost": ("It's been <global_val:pf_an_words> since you married <global_val:pf_an_youname>.  You notice the date, and nobody else does, and that's all right.", "info"),
    "anniv_birth_gone": ("<global_val:pf_an_name> would have been <global_val:pf_an_words> old today.  Nobody says it, but everybody knows.", "bad"),
    "anniv_birth": ("<global_val:pf_an_name> is <global_val:pf_an_words> old today.  Somebody makes a fuss of it.", "good"),
    "scare":       ("<global_val:pf_say_a> is at your side before the thing hits the ground.", "good"),
    "wed_npc":     ("<global_val:pf_say_a> asks <global_val:pf_say_b> to marry them, right there in front of everyone.  <global_val:pf_say_b> says yes, and the whole camp cheers.", "good"),
    "wed_you":     ("Everyone gathers around the fire.  <global_val:pf_say_a> takes your hands, and with all of them as witnesses, you're married.", "good",
                    "Everyone crowds into the room.  <global_val:pf_say_a> takes your hands, and with all of them as witnesses, you're married."),
    "prop_no_npc": ("<global_val:pf_say_a> asks <global_val:pf_say_b> something, low and serious.  <global_val:pf_say_b> shakes their head: not yet.", "info"),
    "prop_notyet": ("<global_val:pf_say_a> squeezes your hand.  \"Not yet.  Ask me again.\"", "info"),
    "prop_wander": ("<global_val:pf_say_a> laughs, not unkindly.  \"I'm not the marrying kind.  You know that.\"", "info"),
    "breakup_npc": ("<global_val:pf_say_a> and <global_val:pf_say_b> had it out tonight, away from the fire.  They aren't together anymore.", "bad",
                    "<global_val:pf_say_a> and <global_val:pf_say_b> had it out tonight, out on the porch.  They aren't together anymore."),
    "breakup_you": ("<global_val:pf_say_a> takes you aside.  \"I can't do this anymore.  I'm sorry.\"", "bad"),
    "left_you":    ("<global_val:pf_say_a> doesn't sit with you tonight.  It's over, and everyone can see it.", "bad"),
    "left_you_for": ("<global_val:pf_say_a> sits with <global_val:pf_say_b> tonight, not with you.  It's over, and everyone knows it.", "bad"),
    "jealous_npc": ("<global_val:pf_jl_cn> sees <global_val:pf_jl_an> making eyes at <global_val:pf_jl_bn>, and goes very quiet.", "bad"),
    "jealous_you": ("You catch <global_val:pf_jl_an> making eyes at <global_val:pf_jl_bn>.", "bad"),
    "service":     ("Tonight the fire is for <global_val:pf_say_b>.  People take turns saying something about them.", "info",
                    "Tonight the evening is for <global_val:pf_say_b>.  People take turns saying something about them."),
    "burial_with": ("You bury <global_val:pf_say_b>.  <global_val:pf_say_a> stands with you at the graveside, and for once nobody keeps watch on the dark.", "info"),
    "burial_alone": ("You bury <global_val:pf_say_b> alone, and say what you can.", "info"),
}
say_eff = [{"if": {"compare_string": [ctx("line"), k]}, "then": [hsay(v[0], v[2], v[1]) if len(v) > 2 else say(v[0], v[1])]} for k, v in LINES.items()]
files["lines.json"] = [eoc("PF_SAY_heart", say_eff, "u = avatar.  v0.2 lines, picked by the context var 'line'.")]

# ============================================================ HEARTS LAB
def nearest(cond_extra=None):
    c = [m("pf_ll_kd = 99"), {"u_location_variable": g("pf_ll_kav")}]
    inline = {"id": "PF_HL_near_%d" % len(HL), "effect": [
        {"u_location_variable": {"u_val": "pf_pos"}},
        {"if": m("distance(u_pf_pos, pf_ll_kav) < pf_ll_kd"), "then": [m("pf_ll_kd = distance(u_pf_pos, pf_ll_kav)"), {"u_set_talker": g("pf_ll_kwho")}]}]}
    if cond_extra:
        inline["condition"] = cond_extra
    c.append({"u_run_npc_eocs": [inline], "local": True, "npc_range": 6})
    return c
HL = []
boost = VNAMES + [m("v_rw = 70"), m("v_rpw = max(v_rpw, 70)"), m("v_rt = 60"), m("v_rpt = max(v_rpt, 60)"), m("v_ra = 65"), m("v_rpa = max(v_rpa, 65)"), m("v_rx = 0")]
HL.append(("PF_HL_ff", "Couple: fast-forward the nearest couple three weeks (strong bonds)",
           "The nearest person who is with someone (you included): their relationship is three weeks old and both feel strongly, so tonight they may become partners, or propose.",
           nearest(m("value_or(u_pf_has_sweet, 0) == 1")) + [
               {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_HL_ff_one", "alpha_talker": g("pf_ll_kwho")}, say("[hearts lab] Three weeks pass for the nearest couple.")],
                "else": [say("[hearts lab] Nobody nearby is with anyone.")]}]))
HL.append(("PF_HL_ff_one", None, None, [
    m("u_pf_sweet_since = time('now') - time('21 d')"), m("u_pf_stage_since = time('now') - time('21 d')"), m("u_pf_prop_last = -1"),
    {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_m_other")}] + boost + [
    {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_hl_a")},
    {"if": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]},
     "then": [{"run_eocs": "PF_HL_ff_partner", "alpha_talker": "avatar"}],
     "else": [{"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
              {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_HL_ff_partner", "alpha_talker": g("pf_find_who")}]}]}]))
HL.append(("PF_HL_ff_partner", None, None, [
    m("u_pf_sweet_since = time('now') - time('21 d')"), m("u_pf_stage_since = time('now') - time('21 d')"), m("u_pf_prop_last = -1"),
    {"copy_var": g("pf_hl_a"), "target_var": g("pf_m_other")}] + boost))
HL.append(("PF_HL_us", "Couple: you and the nearest adult are partners of three weeks",
           "Makes you and the nearest adult (not your ex) partners (stage 2, three weeks), with strong feelings on their side, so at the next fire they may propose to you.",
           [{"copy_var": {"u_val": "pf_ex"}, "target_var": g("pf_hl_avex")}] +
           nearest({"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18"), {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_hl_avex")]}}]}) + [
               {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_HL_us_one", "alpha_talker": g("pf_ll_kwho"), "beta_talker": "avatar"},
                                                    say("[hearts lab] You and the nearest adult have been together three weeks.")],
                "else": [say("[hearts lab] No adult nearby.")]}]))
HL.append(("PF_HL_us_one", None, None, [
    {"run_eocs": "PF_ID_ensure"}, {"run_eocs": "PF_ID_ensure", "alpha_talker": "npc"},
    {"set_string_var": "AVATAR", "target_var": {"u_val": "pf_sweet"}}, {"copy_var": {"u_val": "pf_uid"}, "target_var": {"npc_val": "pf_sweet"}},
    m("u_pf_has_sweet = 1"), m("n_pf_has_sweet = 1"), m("u_pf_rel_stage = 2"), m("n_pf_rel_stage = 2"),
    m("u_pf_sweet_since = time('now') - time('21 d')"), m("n_pf_sweet_since = time('now') - time('21 d')"),
    m("u_pf_stage_since = time('now') - time('21 d')"), m("n_pf_stage_since = time('now') - time('21 d')"),
    m("u_pf_prop_last = -1"), m("u_pf_rom = 1"), m("u_pf_orient = 2"), m("u_pf_commit = 1"), m("u_pf_awk_until = 0"),
    {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}] + boost))
HL.append(("PF_HL_sour", "Couple: the nearest couple falls out (tension 80)",
           "The nearest person who is with someone now feels nothing but tension toward them.  At the next fire, they end it.",
           nearest(m("value_or(u_pf_has_sweet, 0) == 1")) + [
               {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_HL_sour_one", "alpha_talker": g("pf_ll_kwho")}, say("[hearts lab] Something has gone wrong between them.")],
                "else": [say("[hearts lab] Nobody nearby is with anyone.")]}]))
HL.append(("PF_HL_sour_one", None, None, [{"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_m_other")}] + VNAMES + [m("v_rx = 80"), m("v_rw = min(v_rw, 20)")]))
HL.append(("PF_HL_eyes", "Jealousy: a free adult nearby falls for the nearest taken person",
           "Picks the nearest person who is with someone, then another free adult within 10 tiles, who gets a crush (attraction 40) on them.  At the next fire they'll make eyes at them, and the partner may see it.",
           nearest(m("value_or(u_pf_has_sweet, 0) == 1")) + [
               {"if": m("pf_ll_kd < 99"), "then": [
                   {"run_eocs": {"id": "PF_HL_eyes_t", "effect": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_hl_t")}, {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_hl_ts")}]}, "alpha_talker": g("pf_ll_kwho")},
                   m("pf_hl_g = 0"),
                   {"u_run_npc_eocs": ["PF_HL_eyes_g"], "local": True, "npc_range": 10},
                   {"if": m("pf_hl_g == 1"), "then": [m("pf_rom_force_glance = 1"), say("[hearts lab] Someone has a crush on a taken person.")],
                    "else": [say("[hearts lab] No free adult within 10 tiles.")]}],
                "else": [say("[hearts lab] Nobody nearby is with anyone.")]}]))
HL.append(("PF_HL_eyes_g", None, None, [
    {"run_eocs": "PF_ID_ensure"},
    {"if": {"and": [m("pf_hl_g == 0"), m("value_or(u_pf_has_sweet, 0) == 0"), {"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18"),
                    {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_hl_t")]}}, {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_hl_ts")]}}]},
     "then": [m("pf_hl_g = 1"), m("u_pf_rom = 1"), m("u_pf_orient = 2"), m("u_pf_conf_last = time('now')"), m("u_pf_awk_until = 0"),
              {"copy_var": g("pf_hl_t"), "target_var": g("pf_m_other")}] + VNAMES + [
              {"if": m("value_or(v_rl, -1) < 0"), "then": [m("v_rl = time('now')"), m("v_rw = 10"), m("v_rt = 0"), m("v_rx = 0"), m("v_rpw = 10"), m("v_rpt = 0"), m("v_rc = 0.5"), m("v_rf = 1")]},
              m("v_ra = 40"), m("v_rpa = max(value_or(v_rpa, 0), 40)")]}]))
HL.append(("PF_HL_bury", "Grief: dig a grave beside you (burial test)",
           "Turns the nearest bare dirt (within 3 tiles) into a fresh grave and runs the burial signal, as if you'd just finished digging it.  Needs a death someone cared about in the last two weeks.",
           [{"u_location_variable": g("pf_hl_gr"), "terrain": "t_dirt", "target_max_radius": 3,
             "true_eocs": [{"id": "PF_HL_dig", "effect": [{"u_transform_radius": 0, "ter_furn_transform": "PF_HL_grave", "target_var": g("pf_hl_gr")}]}],
             "false_eocs": [{"id": "PF_HL_nodirt", "effect": [say("[hearts lab] No bare dirt within 3 tiles to dig in.")]}]},
            {"run_eocs": "PF_HEART_burial_signal", "variables": {"activity": "ACT_BUILD"}},
            {"if": m("value_or(pf_unburied, 0) == 1"), "then": [say("[hearts lab] (No grave was found, or nobody cared about the last death.)")]}]))
HL.append(("PF_HL_stats", "Stats: hearts",
           "Weddings, breakups, widowed, jealousy, and the last death waiting for a remembrance or a burial.",
           [m("pf_hs_a = value_or(pf_weddings_total, 0)"), m("pf_hs_b = value_or(pf_breakups_total, 0)"), m("pf_hs_c = value_or(pf_widowed_total, 0)"),
            m("pf_hs_d = value_or(pf_jealousy_total, 0)"), m("pf_hs_e = value_or(pf_unmourned, 0)"), m("pf_hs_f = value_or(pf_unburied, 0)"), m("pf_hs_g = value_or(pf_jn_count, 0)"),
            m("pf_hs_h = value_or(pf_engagements_total, 0)"), m("pf_hs_i = value_or(pf_ev_n, 0)"),
            say("[hearts] engagements <global_val:pf_hs_h>, events remembered <global_val:pf_hs_i>, weddings <global_val:pf_hs_a>, breakups <global_val:pf_hs_b>, widowed <global_val:pf_hs_c>, jealousy <global_val:pf_hs_d>, remembrance pending <global_val:pf_hs_e>, burial pending <global_val:pf_hs_f>, journal entries <global_val:pf_hs_g>.")]))
HL.append(("PF_HL_lukewarm", "Proposal: the nearest couple, one eager, one lukewarm",
           "The nearest person who is with someone feels strongly and has waited three weeks as partners; their partner only feels so-so (warmth 40).  At the next fire the eager one proposes and is told not yet.",
           nearest(m("value_or(u_pf_has_sweet, 0) == 1")) + [
               {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_HL_lw_one", "alpha_talker": g("pf_ll_kwho")}, say("[hearts lab] One of them is ready; the other isn't.")],
                "else": [say("[hearts lab] Nobody nearby is with anyone.")]}]))
HL.append(("PF_HL_lw_one", None, None, [
    m("u_pf_rel_stage = 2"), m("u_pf_stage_since = time('now') - time('21 d')"), m("u_pf_prop_last = -1"), m("u_pf_commit = 1"), m("u_pf_engaged = 0"),
    {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_m_other")}] + boost + [
    {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_hl_a")},
    {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
    {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": "PF_HL_lw_partner", "alpha_talker": g("pf_find_who")}]}]))
HL.append(("PF_HL_lw_partner", None, None, [
    m("u_pf_rel_stage = 2"), m("u_pf_stage_since = time('now') - time('21 d')"), m("u_pf_prop_last = time('now')"), m("u_pf_engaged = 0"),
    {"copy_var": g("pf_hl_a"), "target_var": g("pf_m_other")}] + VNAMES + [m("v_rw = 40"), m("v_rpw = 40"), m("v_ra = 30"), m("v_rpa = 30"), m("v_rt = 40")]))
HL.append(("PF_HL_wedday", "Wedding: the nearest engaged couple's day has come",
           "The nearest engaged person and their partner can marry tonight: run an evening to see the wedding.",
           nearest(m("value_or(u_pf_engaged, 0) == 1")) + [
               {"if": m("pf_ll_kd < 99"), "then": [{"run_eocs": "PF_HL_wd_one", "alpha_talker": g("pf_ll_kwho")}, say("[hearts lab] The wedding can be tonight.")],
                "else": [say("[hearts lab] Nobody nearby is engaged.")]}]))
HL.append(("PF_HL_wd_one", None, None, [m("u_pf_wed_t = time('now') - time('1 h')"),
    {"if": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}, "then": [{"run_eocs": {"id": "PF_HL_wd_av", "effect": [m("u_pf_wed_t = time('now') - time('1 h')")]}, "alpha_talker": "avatar"}],
     "else": [{"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid", "alpha_talker": "avatar"},
              {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": {"id": "PF_HL_wd_p", "effect": [m("u_pf_wed_t = time('now') - time('1 h')")]}, "alpha_talker": g("pf_find_who")}]}]}]))
HL.append(("PF_HL_anniv", "Anniversary: the newest death or wedding was a month ago",
           "Moves the most recent recorded death or wedding back 30 days, so the next evening remembers it.",
           [m("pf_hl_ei = (value_or(pf_ev_n, 0) - 1 + 20) % 20"),
            {"set_string_var": "pf_ev_<global_val:pf_hl_ei>_t", "target_var": ctx("et"), "parse_tags": True},
            {"if": m("value_or(pf_ev_n, 0) > 0"), "then": [m("v_et = time('now') - time('30 d')"), say("[hearts lab] A month has passed since the last death or wedding.")],
             "else": [say("[hearts lab] Nothing recorded yet.")]}]))
HL.append(("PF_HL_widow", "Grief: the one you're with dies (widow test)",
           "If you're with someone who is nearby, they die, so you can see what losing them does.",
           [{"if": m("value_or(u_pf_has_sweet, 0) == 1"), "then": [
               {"copy_var": {"u_val": "pf_sweet"}, "target_var": g("pf_find_uid")}, {"run_eocs": "PF_FIND_by_uid"},
               {"if": m("pf_find_ok == 1"), "then": [{"run_eocs": {"id": "PF_HL_widow_die", "effect": ["u_die"]}, "alpha_talker": g("pf_find_who")}],
                "else": [say("[hearts lab] They aren't nearby.")]}],
             "else": [say("[hearts lab] You aren't with anyone.")]}]))
HMENU = [x for x in HL if x[1]]
lab = [eoc("PF_HL_open", [{
    "run_eoc_selector": [i for i, _, _, _ in HMENU], "names": [n for _, n, _, _ in HMENU], "descriptions": [d for _, _, d, _ in HMENU],
    "keys": [c for c in "abcdefghijklmnopqrstuvwxyz"][:len(HMENU)], "title": "Hearts lab (v0.2)", "allow_cancel": True}])]
lab += [eoc(i, eff) for i, _, _, eff in HL]
lab.append({"type": "ter_furn_transform", "id": "PF_HL_grave", "terrain": [{"result": "t_grave_new", "valid_flags": ["DIGGABLE"]}]})
files["lab_hearts.json"] = lab

os.makedirs(OUT, exist_ok=True)
for fname, data in files.items():
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
print("hearts written:", {k: len(v) for k, v in files.items()})
