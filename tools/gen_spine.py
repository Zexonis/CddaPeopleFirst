"""Generates mods/PeopleFirst/spine/*.json: the moment spine (concept §12).

Data flow (all scratch values are globals pf_m_*: moments run to completion one at a time, so globals are safe and
avoid any question of whether context vars propagate between nested EOCs):

  emitter --> PF_MK_<kind>   (alpha = actor, beta = target)   sets kind, tags, deltas, default strength
          --> PF_MOMENT_core  ensure ids, receiver view, actor view, memories, witnesses
          --> PF_VIEW_update  (u = viewer, pf_m_other = the person being viewed)  lazy decay, personality, deltas
"""
import json, os, sys

OUT = sys.argv[1]
def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
def eoc(id_, effect, comment=None, condition=None, **extra):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    o.update(extra)
    if condition: o["condition"] = condition
    o["effect"] = effect
    return o
def name(ctx, pattern):
    return {"set_string_var": pattern, "target_var": {"context_val": ctx}, "parse_tags": True}

TAGS = ["danger", "care", "food", "waste", "play", "ritual", "loss", "humor", "pride", "shame", "loyalty", "romance"]
MEM_SLOTS = 8

# ---------------------------------------------------------------- personality
TRAITS = [
    ("PF_T_SOCIABLE", "Sociable", "Draws warmth from company: meals, fires and play count for more."),
    ("PF_T_LONER", "Loner", "Company wears on them.  Gatherings count for less, quiet kindness for more."),
    ("PF_Q_LOYAL", "Loyal to a fault", "Being covered for, cared for or saved builds trust twice as fast."),
    ("PF_Q_HATES_WASTE", "Hates waste", "Wasted food or supplies sour their view of whoever did it."),
    ("PF_Q_MOTHER_HEN", "Mother hen", "Seeing someone in danger or being cared for makes them care more."),
    ("PF_Q_GALLOWS", "Gallows humor", "Danger rattles them less.  They joke about it afterward."),
    ("PF_Q_PROUD", "Proud", "Pride and shame both hit twice as hard."),
    ("PF_Q_GRUDGE", "Holds grudges", "Tension fades a third as fast."),
    ("PF_Q_FORGIVING", "Forgiving", "Tension fades three times as fast."),
    ("PF_Q_ROMANTIC", "Hopeless romantic", "Falls faster and harder, and loves the little rituals of courting."),
]
personality = []
for tid, nm, desc in TRAITS:
    personality.append({"type": "mutation", "id": tid, "name": {"str": nm}, "points": 0, "valid": False,
                        "purifiable": False, "player_display": False, "description": desc})

personality.append(eoc("PF_PERSONA_roll", [
    m("_r = rand(2)"),
    {"if": m("_r == 0"), "then": [{"u_add_trait": "PF_T_SOCIABLE"}]},
    {"if": m("_r == 1"), "then": [{"u_add_trait": "PF_T_LONER"}]},
    m("_q = rand(4)"),
    {"switch": m("_q"), "cases": [
        {"case": 0, "effect": {"u_add_trait": "PF_Q_LOYAL"}},
        {"case": 1, "effect": {"u_add_trait": "PF_Q_HATES_WASTE"}},
        {"case": 2, "effect": {"u_add_trait": "PF_Q_MOTHER_HEN"}},
        {"case": 3, "effect": {"u_add_trait": "PF_Q_GALLOWS"}},
        {"case": 4, "effect": {"u_add_trait": "PF_Q_PROUD"}},
        {"case": 5, "effect": {"u_add_trait": "PF_Q_GRUDGE"}},
        {"case": 6, "effect": {"u_add_trait": "PF_Q_FORGIVING"}},
        {"case": 7, "effect": {"u_add_trait": "PF_Q_ROMANTIC"}}]},
    m("u_pf_persona = 1"),
    {"run_eocs": "PF_ROM_roll"},
], "u = an NPC meeting the spine for the first time.  One temperament (or none) and one quirk, then their romantic nature."))

personality.append(eoc("PF_ROM_roll", [
    m("u_pf_adult = u_val('age') >= 18"),
    {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("u_pf_adult = 0")]},
    {"if": m("u_pf_adult == 1"),
     "then": [
        m("u_pf_rom = rand(19) >= 3"),
        m("_o = rand(99)"),
        m("u_pf_orient = _o < 70 ? 1 - u_gender() : (_o < 82 ? u_gender() : 2)"),
        m("_k = rand(2)"), m("u_pf_open = _k == 0 ? 0.15 : (_k == 1 ? 0.5 : 0.9)"),
        m("_k = rand(9)"), m("u_pf_commit = _k <= 5 ? 1 : (_k <= 8 ? 2 : 3)"),
        m("u_pf_rtype = rand(2)")],
     "else": [m("u_pf_rom = 0")]},
    m("u_pf_rom_rolled = 1"),
    {"run_eocs": "PF_REG_write"},
], "u = an NPC.  Their own romantic nature, rolled once.  Adults only: children are never romantic (PF_CHILD or under 18; enforced again wherever attraction is computed).  u_pf_rom 0/1 (about 15% aromantic); u_pf_orient 0 = drawn to women, 1 = men, 2 = both (about 70% opposite sex, 12% same, 18% both); u_pf_open 0.15 / 0.5 / 0.9 = set in their feelings / can warm up / easily swayed; u_pf_commit 1 devoted, 2 casual, 3 wandering eye (v0.2 reads it); u_pf_rtype 0 likes sociable people, 1 likes loners, 2 no type."))

personality.append(eoc("PF_REG_write", [
    {"set_string_var": "pf_reg_<u_val:pf_uid>_g", "target_var": {"context_val": "rg"}, "parse_tags": True},
    {"set_string_var": "pf_reg_<u_val:pf_uid>_a", "target_var": {"context_val": "rad"}, "parse_tags": True},
    {"set_string_var": "pf_reg_<u_val:pf_uid>_tm", "target_var": {"context_val": "rtm"}, "parse_tags": True},
    m("v_rg = u_gender()"), m("v_rad = value_or(u_pf_adult, 0)"),
    m("v_rtm = 0"),
    {"if": {"u_has_trait": "PF_T_SOCIABLE"}, "then": [m("v_rtm = 1")]},
    {"if": {"u_has_trait": "PF_T_LONER"}, "then": [m("v_rtm = 2")]},
    {"set_string_var": "pf_reg_<u_val:pf_uid>_q", "target_var": {"context_val": "rq"}, "parse_tags": True}, m("v_rq = -1"),
    {"if": {"u_has_trait": "PF_Q_LOYAL"}, "then": [m("v_rq = 0")]},
    {"if": {"u_has_trait": "PF_Q_HATES_WASTE"}, "then": [m("v_rq = 1")]},
    {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [m("v_rq = 2")]},
    {"if": {"u_has_trait": "PF_Q_GALLOWS"}, "then": [m("v_rq = 3")]},
    {"if": {"u_has_trait": "PF_Q_PROUD"}, "then": [m("v_rq = 4")]},
    {"if": {"u_has_trait": "PF_Q_GRUDGE"}, "then": [m("v_rq = 5")]},
    {"if": {"u_has_trait": "PF_Q_FORGIVING"}, "then": [m("v_rq = 6")]},
    {"if": {"u_has_trait": "PF_Q_ROMANTIC"}, "then": [m("v_rq = 7")]},
    {"set_string_var": "pf_name_<u_val:pf_uid>", "target_var": {"context_val": "rnm"}, "parse_tags": True},
    {"set_string_var": "<u_name>", "target_var": {"var_val": "rnm"}, "parse_tags": True},
    m("u_pf_reg_done = 1"),
], "u = anyone with a pf_uid.  Publishes what others need to know about them without a talker (gender, adult, temperament, and their name in pf_name_<uid>) in globals, so views can be computed off-screen, one person at a time."))
personality.append(eoc("PF_REG_name", [
    {"set_string_var": "pf_name_<u_val:pf_uid>", "target_var": {"context_val": "rnm"}, "parse_tags": True},
    {"set_string_var": "<u_name>", "target_var": {"var_val": "rnm"}, "parse_tags": True},
], "u = someone with a pf_uid.  Refreshes their directory name (full run: a band child renamed to the family surname after registering "
   "still showed the old surname in People you know).  Run after every rename, and by the People nearby scan.",
    condition={"math": ["has_var(u_pf_uid)"]}))

# u = viewer.  pf_m_role: 1 = receiver, 2 = actor, 3 = witness.  Produces pf_m_mulw / mult / mulx.
weigh = [m("pf_m_mulw = 1"), m("pf_m_mult = 1"), m("pf_m_mulx = 1")]
def rule(trait, cond, effects):
    c = {"and": [{"u_has_trait": trait}, m(cond)]} if cond else {"u_has_trait": trait}
    weigh.append({"if": c, "then": [m(e) for e in effects]})
rule("PF_T_SOCIABLE", "pf_m_tag_food + pf_m_tag_ritual + pf_m_tag_play > 0", ["pf_m_mulw *= 1.5"])
rule("PF_T_LONER", "pf_m_tag_ritual + pf_m_tag_play > 0", ["pf_m_mulw *= 0.5"])
rule("PF_T_LONER", "(pf_m_tag_care > 0) * (pf_m_role == 1)", ["pf_m_mulw *= 1.5"])
rule("PF_Q_LOYAL", "(pf_m_tag_loyalty + pf_m_tag_care > 0) * (pf_m_role == 1)", ["pf_m_mult *= 2"])
rule("PF_Q_HATES_WASTE", "pf_m_tag_waste > 0", ["pf_m_mulx *= 3", "pf_m_mulw *= 0.5"])
rule("PF_Q_MOTHER_HEN", "(pf_m_tag_danger + pf_m_tag_care > 0) * (pf_m_role == 3)", ["pf_m_mulw *= 2"])
rule("PF_Q_GALLOWS", "pf_m_tag_danger > 0", ["pf_m_mulx *= 0.5"])
rule("PF_Q_PROUD", "pf_m_tag_pride + pf_m_tag_shame > 0", ["pf_m_mulw *= 2", "pf_m_mulx *= 2"])
rule("PF_Q_ROMANTIC", "pf_m_tag_romance > 0", ["pf_m_mulw *= 1.3"])
personality.append(eoc("PF_PERSONA_weigh", weigh,
    "u = viewer.  Turns the moment's tags (pf_m_tag_*) and the viewer's role (pf_m_role) into multipliers on warmth, trust and tension.  Quirks never touch bonds directly; this is the only place they act."))

# ---------------------------------------------------------------- identity & known people
ids = [
    eoc("PF_ID_ensure", [
        {"if": "u_is_avatar",
         "then": [{"set_string_var": "AVATAR", "target_var": {"u_val": "pf_uid"}},
                  {"if": m("value_or(u_pf_reg_done, 0) == 0"), "then": [m("u_pf_adult = 1"), {"run_eocs": "PF_REG_write"}]}],
         "else": [{"if": m("has_var(u_pf_uid) == 0"),
                   "then": [m("pf_vid_n = value_or(pf_vid_n, 0) + 1"),
                            {"set_string_var": "PF_V_<global_val:pf_vid_n>", "target_var": {"u_val": "pf_uid"}, "parse_tags": True}]},
                  {"if": {"not": {"u_has_trait": "PF_PERSON"}}, "then": [{"u_add_trait": "PF_PERSON"}]},
                  {"if": m("value_or(u_pf_persona, 0) == 0"), "then": [{"run_eocs": "PF_PERSONA_roll"}]},
                  {"if": m("value_or(u_pf_rom_rolled, 0) == 0"), "then": [{"run_eocs": "PF_ROM_roll"}]},
                  {"if": m("value_or(u_pf_reg_done, 0) == 0"), "then": [{"run_eocs": "PF_REG_write"}]}]},
    ], "u = anyone.  Gives them a stable id for naming views (A-Life agents already have PF_P_n; others get PF_V_n; the avatar is AVATAR) and a personality on first contact."),
    eoc("PF_KNOWN_add", [
        m("u_pf_known_n = value_or(u_pf_known_n, 0)"),
        {"if": m("u_pf_known_n < pf_known_cap"),
         "then": [name("ref", "u_pf_known_<u_val:pf_known_n>"),
                  {"copy_var": g("pf_m_other"), "target_var": {"var_val": "ref"}},
                  m("u_pf_known_n = value_or(u_pf_known_n, 0) + 1")],
         "else": [m("pf_known_full_total = value_or(pf_known_full_total, 0) + 1")]},
    ], "u = viewer.  Appends pf_m_other to the viewer's known-people list (array u_pf_known_<n>).  At the cap new people are not listed (their view still exists); eviction comes with the Dunbar layers."),
]

# ---------------------------------------------------------------- views
view_names = [name("rw", "u_pf_v_<global_val:pf_m_other>_w"), name("rt", "u_pf_v_<global_val:pf_m_other>_t"),
              name("rx", "u_pf_v_<global_val:pf_m_other>_x"), name("rpw", "u_pf_v_<global_val:pf_m_other>_pw"),
              name("rpt", "u_pf_v_<global_val:pf_m_other>_pt"), name("rl", "u_pf_v_<global_val:pf_m_other>_l"),
              name("ra", "u_pf_v_<global_val:pf_m_other>_a"), name("rpa", "u_pf_v_<global_val:pf_m_other>_pa"),
              name("rc", "u_pf_v_<global_val:pf_m_other>_c"), name("rf", "u_pf_v_<global_val:pf_m_other>_f"),
              name("og", "pf_reg_<global_val:pf_m_other>_g"), name("oa", "pf_reg_<global_val:pf_m_other>_a"),
              name("otm", "pf_reg_<global_val:pf_m_other>_tm")]
views = [
    eoc("PF_VIEW_names", view_names, "Sets context vars rw/rt/rx/rpw/rpt/rl to the names of u's view of pf_m_other.  Read and write them with v_rw etc. in math."),
    eoc("PF_VIEW_update", view_names + [
        {"if": m("value_or(v_rl, -1) < 0"),
         "then": [m("v_rw = 0"), m("v_rt = 0"), m("v_rx = 0"), m("v_rpw = 0"), m("v_rpt = 0"), m("v_rl = time('now')"),
                  {"run_eocs": "PF_KNOWN_add"}, m("pf_views_created = value_or(pf_views_created, 0) + 1")]},
        # chemistry, rolled once per pair at first meeting (or lazily for views made before chemistry existed)
        {"if": m("value_or(v_rf, -1) < 0"), "then": [
            m("_mt = 0"),
            {"if": {"u_has_trait": "PF_T_SOCIABLE"}, "then": [m("_mt = 1")]},
            {"if": {"u_has_trait": "PF_T_LONER"}, "then": [m("_mt = 2")]},
            m("v_rf = 0.6 + rand(80) / 100 + ((_mt > 0) * (_mt == value_or(v_otm, 0))) * 0.15 - ((_mt > 0) * (value_or(v_otm, 0) > 0) * (_mt != value_or(v_otm, 0))) * 0.1"),
            m("v_rc = rand(100) / 100"), m("v_ra = 0"), m("v_rpa = 0")]},
        m("_d = (time('now') - v_rl) / time('1 d')"),
        m("_st = 0"),
        {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, g("pf_m_other")]}]},
         "then": [m("_st = value_or(u_pf_rel_stage, 1)")]},
        m("_dm = 1 - 0.25 * _st"),
        m("_qx = 1"),
        {"if": {"u_has_trait": "PF_Q_GRUDGE"}, "then": [m("_qx = 0.33")]},
        {"if": {"u_has_trait": "PF_Q_FORGIVING"}, "then": [m("_qx = 3")]},
        m("v_rw = v_rw >= 0 ? max(min(v_rw, v_rpw * pf_floor_w), v_rw - _d * pf_decay_w * _dm) : min(0, v_rw + _d * pf_decay_w)"),
        m("v_rt = v_rt >= 0 ? max(min(v_rt, v_rpt * pf_floor_t), v_rt - _d * pf_decay_t * _dm) : min(0, v_rt + _d * pf_decay_t)"),
        m("v_rx = max(0, v_rx - _d * pf_decay_x * _qx)"),
        m("v_ra = max(min(v_ra, v_rpa * (0.3 + 0.15 * _st)), v_ra - _d * 0.25 * _dm)"),
        {"run_eocs": "PF_PERSONA_weigh"},
        m("_s = pf_m_str / 50"),
        m("_gw = pf_m_dw * _s * pf_m_mulw"),
        m("_gw = _gw > 0 ? _gw * v_rf : _gw"),
        m("_gt = pf_m_dt * _s * pf_m_mult"),
        m("_gx = pf_m_dx * _s * pf_m_mulx"),
        m("v_rw = clamp(v_rw + (_gw > 0 ? _gw * (1 - max(v_rw, 0) / 110) : _gw), -100, 100)"),
        m("v_rt = clamp(v_rt + (_gt > 0 ? _gt * (1 - max(v_rt, 0) / 110) : _gt), -100, 100)"),
        m("v_rx = clamp(v_rx + _gx, 0, 100)"),
        # attraction: only adult to adult, only if the viewer is romantic and drawn to the other's sex.  Never children (checked twice).
        m("_el = (value_or(u_pf_rom, 0) == 1) * (value_or(u_pf_adult, 0) == 1) * (value_or(v_oa, 0) == 1) * ((value_or(u_pf_orient, -1) == 2) + (value_or(u_pf_orient, -1) == value_or(v_og, -2)) > 0)"),
        {"if": {"u_has_trait": "PF_CHILD"}, "then": [m("_el = 0")]},
        {"if": m("_el > 0"), "then": [
            m("_ch = max(v_rc + ((u_pf_rtype == 0) * (value_or(v_otm, 0) == 1) + (u_pf_rtype == 1) * (value_or(v_otm, 0) == 2)) * 0.2, u_pf_open * max(v_rw, 0) / 100)"),
            m("_ga = (_gw > 0 ? _gw * _ch * 1.2 : _gw * 0.5) + pf_m_da * _s"),
            {"if": {"u_has_trait": "PF_Q_ROMANTIC"}, "then": [m("_ga = _ga > 0 ? _ga * 1.6 : _ga")]},
            m("v_ra = clamp(v_ra + (_ga > 0 ? _ga * (1 - v_ra / 110) : _ga), 0, 100)"),
            m("v_rpa = max(v_rpa, v_ra)")]},
        m("v_rpw = max(v_rpw, v_rw)"),
        m("v_rpt = max(v_rpt, v_rt)"),
        m("v_rl = time('now')"),
        {"if": m("pf_m_str >= pf_mem_min"), "then": [{"run_eocs": "PF_MEM_store"}]},
    ], "u = viewer, pf_m_other = who they are looking at, pf_m_dw/dt/dx/da = base deltas for this role.  Friendship chemistry (v_rf, 0.6-1.4, temperament match +0.15, clash -0.1) scales warmth gains: some people just click, some never will.  Romantic chemistry (v_rc) plus their 'type' scales attraction; open people warm up as warmth grows, set ones don't.  Lazy decay (months, floored at a share of the peak: old friends stay meaningful), then personality, then the deltas with diminishing returns near the top.  No per-person ticking anywhere: a view only costs CPU when something happens."),
    eoc("PF_VIEW_read", view_names + [
        m("_d = (time('now') - value_or(v_rl, time('now'))) / time('1 d')"),
        m("_st = 0"),
        {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, g("pf_m_other")]}]},
         "then": [m("_st = value_or(u_pf_rel_stage, 1)")]},
        m("_dm = 1 - 0.25 * _st"),
        m("pf_read_w = value_or(v_rw, 0)"), m("pf_read_t = value_or(v_rt, 0)"), m("pf_read_x = value_or(v_rx, 0)"),
        m("pf_read_w = pf_read_w >= 0 ? max(min(pf_read_w, value_or(v_rpw, 0) * pf_floor_w), pf_read_w - _d * pf_decay_w * _dm) : min(0, pf_read_w + _d * pf_decay_w)"),
        m("pf_read_t = pf_read_t >= 0 ? max(min(pf_read_t, value_or(v_rpt, 0) * pf_floor_t), pf_read_t - _d * pf_decay_t * _dm) : min(0, pf_read_t + _d * pf_decay_t)"),
        m("_qx = 1"),
        {"if": {"u_has_trait": "PF_Q_GRUDGE"}, "then": [m("_qx = 0.33")]},
        {"if": {"u_has_trait": "PF_Q_FORGIVING"}, "then": [m("_qx = 3")]},
        m("pf_read_x = max(0, pf_read_x - _d * pf_decay_x * _qx)"),
        m("pf_read_a = max(min(value_or(v_ra, 0), value_or(v_rpa, 0) * (0.3 + 0.15 * _st)), value_or(v_ra, 0) - _d * 0.25 * _dm)"),
        m("pf_read_score = (pf_read_w + pf_read_t) / 2"),
        m("pf_read_tier = (pf_read_score >= 10) + (pf_read_score >= 30) + (pf_read_score >= 55) + (pf_read_score >= 80)"),
        {"switch": m("pf_read_tier"), "cases": [
            {"case": 0, "effect": {"set_string_var": "stranger", "target_var": g("pf_read_tier_name")}},
            {"case": 1, "effect": {"set_string_var": "acquaintance", "target_var": g("pf_read_tier_name")}},
            {"case": 2, "effect": {"set_string_var": "companion", "target_var": g("pf_read_tier_name")}},
            {"case": 3, "effect": {"set_string_var": "close", "target_var": g("pf_read_tier_name")}},
            {"case": 4, "effect": {"set_string_var": "devoted", "target_var": g("pf_read_tier_name")}}]},
    ], "u = viewer.  Reads u's view of pf_m_other with decay applied (without writing it back) into pf_read_w/t/x, a tier 0-4 and its name.  Readers and the menu use this."),
]

# ---------------------------------------------------------------- memories
def mem_names(idx_tag):
    return [name("mk", f"u_pf_mem_{idx_tag}_kind"), name("mw", f"u_pf_mem_{idx_tag}_with"),
            name("ms", f"u_pf_mem_{idx_tag}_str"), name("mt", f"u_pf_mem_{idx_tag}_t"), name("mr", f"u_pf_mem_{idx_tag}_rc"),
            name("mo", f"u_pf_mem_{idx_tag}_role")]
mem = [
    eoc("PF_MEM_store", [
        {"if": "u_is_avatar", "then": [{"run_eocs": "PF_JOURNAL_add"}]},
        m("u_pf_mem_count = value_or(u_pf_mem_count, 0)"),
        {"if": m("u_pf_mem_count < %d" % MEM_SLOTS),
         "then": [m("pf_mslot = u_pf_mem_count"), m("u_pf_mem_count += 1"), m("_ok = 1")],
         "else": [m("pf_mi = 0"), m("pf_mmin = 1000"), m("pf_mslot = 0"),
                  {"run_eocs": "PF_MEM_scan_weakest", "condition": m("pf_mi < %d" % MEM_SLOTS), "iterations": MEM_SLOTS + 1},
                  m("_ok = pf_m_str > pf_mmin")]},
        {"if": m("_ok"), "then": mem_names("<global_val:pf_mslot>") + [
            {"copy_var": g("pf_m_kind"), "target_var": {"var_val": "mk"}},
            {"copy_var": g("pf_m_other"), "target_var": {"var_val": "mw"}},
            m("v_ms = pf_m_str"), m("v_mt = time('now')"), m("v_mr = 0"), m("v_mo = pf_m_role"),
            m("u_pf_mem_next = (pf_mslot + 1) %% %d" % MEM_SLOTS),
            m("pf_memories_total = value_or(pf_memories_total, 0) + 1")]},
    ], "u = someone who lived or saw a strong moment.  %d memory slots: kind, with whom, strength, when, told-yet, and their role (1 = it was done to them, 2 = they did it, 3 = they saw it).  When full, the new memory replaces the weakest one, and only if it is stronger.  Big moments outlive small ones." % MEM_SLOTS),
    eoc("PF_MEM_scan_weakest", [
        name("ms", "u_pf_mem_<global_val:pf_mi>_str"),
        {"if": m("value_or(v_ms, 0) < pf_mmin"), "then": [m("pf_mmin = value_or(v_ms, 0)"), m("pf_mslot = pf_mi")]},
        m("pf_mi += 1"),
    ]),
]

# ---------------------------------------------------------------- moments
def role_set(prefix):
    return [m(f"pf_m_dw = pf_m_{prefix}w"), m(f"pf_m_dt = pf_m_{prefix}t"), m(f"pf_m_dx = pf_m_{prefix}x"), m(f"pf_m_da = pf_m_{prefix}a")]

core = [
    {"run_eocs": "PF_ID_ensure"},
    {"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_m_actor")},
    {"if": "has_beta", "then": [
        {"run_eocs": "PF_ID_ensure", "alpha_talker": "npc"},
        {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_m_target")},
        # the target's view of the actor
        {"copy_var": g("pf_m_actor"), "target_var": g("pf_m_other")},
        m("pf_m_role = 1")] + role_set("r") + [
        {"run_eocs": "PF_VIEW_update", "alpha_talker": "npc"},
        # the actor's view of the target
        {"copy_var": g("pf_m_target"), "target_var": g("pf_m_other")},
        m("pf_m_role = 2")] + role_set("a") + [
        {"run_eocs": "PF_VIEW_update"}],
     "else": [{"set_string_var": "none", "target_var": g("pf_m_target")}]},
    {"if": m("pf_m_str >= pf_wit_min"), "then": [
        {"u_run_npc_eocs": ["PF_MOMENT_witness"], "local": True, "npc_range": 15, "npc_must_see": True}]},
    m("pf_moments_total = value_or(pf_moments_total, 0) + 1"),
]
moments = [eoc("PF_MOMENT_core", core,
    "Alpha = actor, beta = target (optional).  Called by PF_MK_<kind> after it has set kind, tags, strength and per-role deltas.  Updates the target's view of the actor, the actor's view of the target, memories, and (for strong moments) every NPC who saw it.")]
moments.append(eoc("PF_MOMENT_witness", [
    {"run_eocs": "PF_ID_ensure"},
    {"if": {"and": [{"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_m_actor")]}},
                    {"not": {"compare_string": [{"u_val": "pf_uid"}, g("pf_m_target")]}}]},
     "then": [{"copy_var": g("pf_m_actor"), "target_var": g("pf_m_other")}, m("pf_m_role = 3")] + role_set("w") + [
              {"run_eocs": "PF_VIEW_update"}, m("pf_witnessed_total = value_or(pf_witnessed_total, 0) + 1")]},
], "u = an NPC who saw a strong moment (not the actor or target).  Updates their view of the actor and lets them remember it."))

# kind: (tags, default strength, receiver w/t/x, actor w/t/x, witness w/t/x, description)
KINDS = {
    "meal_shared":   (["food", "ritual"], 30, (3, 2, 0), (3, 1, 0), (0, 0, 0), "Ate together.  The one fed trusts a little more (playtest 3: sharing scarce food is a trust signal; with trust +1 a lone start took about 11 days to win anyone over)."),
    "care_given":    (["care"], 50, (6, 5, 0), (2, 0, 0), (2, 2, 0), "The actor cared for the target (warmth, food, bandages)."),
    "saved_life":    (["danger", "care", "loyalty"], 90, (15, 20, 0), (10, 6, 0), (3, 6, 0), "The actor saved the target's life.  Two-way: the saved one is grateful, and the saver grows protective of them."),
    "shared_danger": (["danger"], 60, (5, 4, 0), (5, 4, 0), (1, 1, 0), "Faced danger side by side."),
    "watch_covered": (["care", "loyalty"], 40, (3, 8, 0), (1, 0, 0), (0, 1, 0), "The actor took the target's watch."),
    "fire_evening":  (["ritual", "play"], 20, (2, 0, 0), (2, 0, 0), (0, 0, 0), "A quiet evening by the fire together."),
    "gift":          (["care"], 30, (5, 1, 0), (1, 0, 0), (0, 0, 0), "The actor gave the target something they liked."),
    "argument":      ([], 40, (-2, 0, 20), (-1, 0, 15), (0, 0, 0), "They argued."),
    "insult":        (["shame"], 40, (-5, -2, 15), (0, 0, 2), (-1, -1, 0), "The actor insulted the target."),
    "wasted_food":   (["food", "waste"], 30, (-1, 0, 6), (0, 0, 0), (0, 0, 3), "The actor wasted food in front of the target."),
    "betrayal":      (["loss"], 90, (-20, -40, 30), (0, 0, 0), (-5, -15, 5), "The actor betrayed the target."),
    "near_death":    (["danger"], 70, (0, 0, 0), (0, 0, 0), (4, 0, 0), "The actor nearly died; the people who saw it were shaken (no target)."),
    "memory_recalled": (["ritual"], 30, (2, 1, 0), (2, 1, 0), (0, 0, 0), "The actor brought up a shared memory with the target."),
    "teased":        (["humor", "shame"], 30, (1, 0, 6), (1, 0, 0), (0, 0, 0), "The actor teased the target.  Proud targets take it badly."),
    "bicker":        ([], 25, (-1, 0, 4), (-1, 0, 4), (0, 0, 0), "Petty bickering; keeps existing tension alive."),
    "flirt":         (["romance", "play"], 30, (2, 0, 0), (1, 0, 0), (0, 0, 0), "The actor flirted with the target."),
    "confession":    (["romance"], 60, (3, 1, 0), (1, 0, 0), (0, 0, 0), "The actor told the target how they feel."),
    "rejected":      (["romance", "shame"], 50, (-2, 0, 6), (0, 0, 3), (0, 0, 0), "The actor turned the target down.  It stings, and things are awkward for a while."),
    "courting":      (["romance", "ritual"], 35, (3, 1, 0), (3, 1, 0), (0, 0, 0), "Time spent together as sweethearts."),
    "jealous":       (["romance"], 50, (-2, -3, 10), (0, 0, 0), (0, 0, 0), "The viewer saw the target make eyes at someone who is taken (or at someone else while taken).  One-sided."),
    "breakup":       (["loss", "shame"], 70, (-6, -4, 10), (-3, 0, 6), (0, 0, 0), "The actor ended it with the target."),
    "partnered":     (["romance", "ritual"], 55, (4, 3, 0), (4, 3, 0), (0, 0, 0), "Sweethearts became partners."),
    "wedding":       (["romance", "ritual"], 85, (8, 6, 0), (8, 6, 0), (4, 2, 0), "The actor and the target married, with everyone at the fire as witnesses."),
    "proposal_declined": (["romance"], 45, (-1, 0, 3), (0, 0, 1), (0, 0, 0), "The actor proposed and the target said not yet."),
    "funeral":       (["ritual", "loss"], 50, (3, 2, 0), (3, 2, 0), (1, 1, 0), "Mourned someone together."),
    "birth":         (["ritual", "care"], 90, (6, 4, 0), (6, 4, 0), (5, 2, 0), "A child was born (half moment: the viewer was there, or it was theirs)."),
    "adopted":       (["care", "loyalty"], 80, (10, 8, 0), (6, 2, 0), (3, 2, 0), "The actor took the target (a child) in."),
    "parenting":     (["care"], 30, (4, 2, 0), (2, 0, 0), (1, 0, 0), "The actor looked after the target (a baby or child)."),
    "taught":        (["care", "play"], 35, (4, 3, 0), (3, 1, 0), (0, 0, 0), "The actor taught the target something (a skill, a trick, how things are done)."),
    "welcomed":      (["loyalty", "ritual"], 60, (6, 6, 0), (4, 4, 0), (1, 1, 0), "The actor took the target's people in: they live under one roof now."),
    "secret_kept":   (["loyalty"], 60, (4, 10, 0), (2, 2, 0), (0, 0, 0), "The actor found out what the target really is, and kept it to themselves."),
    "frightened":    (["danger"], 60, (-4, -8, 15), (0, 0, 0), (0, 0, 0), "The viewer saw something in the target that frightened them.  One-sided (PF_MV_frightened)."),
    "ran_off":       (["danger", "shame"], 50, (-3, -10, 6), (0, 0, 3), (0, -4, 0), "The actor ran while the target was in danger.  The target trusts them less; so does everyone who saw it."),
    "lost_companion": (["loss"], 70, (0, 0, 0), (0, 0, 0), (0, 0, 0), "The target died and the viewer lost them.  Memory only: a view of the dead is not changed (used one-sided, PF_MV_lost_companion)."),
    # v0.6 The Keep, pass 1 (gen_keep.py): the meeting
    "voted_for":     (["loyalty"], 40, (2, 2, 0), (1, 3, 0), (0, 0, 0), "The actor voted for the target to lead the place."),
    "ruled_for":     (["loyalty"], 45, (3, 6, 0), (1, 1, 0), (0, 1, 0), "The actor, as chief, took the target's side in a quarrel."),
    "ruled_against": (["shame"], 45, (-3, -4, 12), (0, 0, 3), (0, 0, 0), "The actor, as chief, ruled against the target in a quarrel."),
    "made_peace":    (["ritual"], 40, (2, 1, -15), (2, 1, -15), (0, 0, 0), "The actor and the target settled a quarrel and shook on it."),
    # v0.7 open threads (gen_away.py): coming home
    "welcomed_back": (["loyalty", "ritual"], 45, (3, 2, 0), (4, 1, 0), (1, 0, 0), "The target came home after days away and the actor was the first to meet them."),
}
# attraction deltas (receiver, actor); everything else 0.  Only applied where attraction is allowed at all (adults, orientation).
ATTR = {"flirt": (6, 2), "confession": (5, 0), "rejected": (-10, 0), "courting": (6, 6), "saved_life": (4, 0),
        "partnered": (4, 4), "wedding": (8, 8), "breakup": (-15, -10), "proposal_declined": (-2, 0)}
for kind, (tags, dstr, r, a, w, desc) in KINDS.items():
    ra_, aa_ = ATTR.get(kind, (0, 0))
    eff = [{"set_string_var": kind, "target_var": g("pf_m_kind")}]
    eff += [m(f"pf_m_tag_{t} = {1 if t in tags else 0}") for t in TAGS]
    eff += [m(f"pf_m_str = value_or(pf_m_str_in, -1) > 0 ? pf_m_str_in : {dstr}"), m("pf_m_str_in = -1")]
    for pre, vals in (("r", r), ("a", a), ("w", w)):
        eff += [m(f"pf_m_{pre}w = {vals[0]}"), m(f"pf_m_{pre}t = {vals[1]}"), m(f"pf_m_{pre}x = {vals[2]}")]
    eff += [m(f"pf_m_ra = {ra_}"), m(f"pf_m_aa = {aa_}"), m("pf_m_wa = 0")]
    eff.append({"run_eocs": "PF_MOMENT_core"})
    moments.append(eoc(f"PF_MK_{kind}", eff,
        f"Moment '{kind}': {desc}  Alpha = actor, beta = target.  Optional strength: set pf_m_str_in first (default {dstr})."))
    # one-sided "half moment": updates only u's view of pf_m_other.  No second talker needed, so it works by unique id off-screen.
    mv = [{"set_string_var": kind, "target_var": g("pf_m_kind")}]
    mv += [m(f"pf_m_tag_{t} = {1 if t in tags else 0}") for t in TAGS]
    mv += [m(f"pf_m_str = value_or(pf_m_str_in, -1) > 0 ? pf_m_str_in : {dstr}"), m("pf_m_str_in = -1"), m("pf_m_role = value_or(pf_mv_role, 1)")]
    mv += [m(f"pf_m_dw = pf_m_role == 2 ? {a[0]} : {r[0]}"), m(f"pf_m_dt = pf_m_role == 2 ? {a[1]} : {r[1]}"), m(f"pf_m_dx = pf_m_role == 2 ? {a[2]} : {r[2]}"),
           m(f"pf_m_da = pf_m_role == 2 ? {aa_} : {ra_}")]
    mv.append({"run_eocs": "PF_VIEW_update"})
    moments.append(eoc(f"PF_MV_{kind}", mv,
        f"Half moment '{kind}': updates only u's view of pf_m_other (role pf_mv_role: 1 = it happened to u, 2 = u did it).  For off-screen life, where only one person at a time can be reached (by unique id)."))

os.makedirs(OUT, exist_ok=True)
for fname, data in (("personality.json", personality), ("ids.json", ids), ("views.json", views),
                    ("memories.json", mem), ("moments.json", moments)):
    json.dump(data, open(os.path.join(OUT, fname), "w", encoding="utf-8", newline="\n"), indent=2)
print("spine written:", sum(len(x) for x in (personality, ids, views, mem, moments)), "objects")
