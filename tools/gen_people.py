"""Generates mods/PeopleFirst/people/people_menu.json: the People menu prototype (Nearby + Person screens)."""
import json, sys
N = 20
def m(e): return {"math": [e]}
def g(n): return {"global_val": n}
def eoc(id_, effect, comment=None, condition=None, **extra):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    o.update(extra)
    if condition: o["condition"] = condition
    o["effect"] = effect
    return o
def msg(t, ty="info"): return {"u_message": t, "type": ty}
def slotname(prefix): return {"set_string_var": prefix + "<global_val:pf_pm_n>", "target_var": {"context_val": "ref"}, "parse_tags": True}

PARTS = ["torso", "head", "eyes", "mouth", "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r", "foot_l", "foot_r"]
HP_PARTS = ["torso", "head", "arm_l", "arm_r", "leg_l", "leg_r"]
# the selected person (beta) is hurt: a main part at 80% or less, or bleeding / bitten anywhere (gen_life HURT, for n)
N_HURT = {"or": [m(f"n_hp('{p}') <= n_hp_max('{p}') * 0.8") for p in HP_PARTS]
                + [{"npc_has_effect": e, "bodypart": bp} for e in ("bleed", "bite") for bp in PARTS] + [{"npc_has_effect": e} for e in ("bleed", "bite")]}
out = []
out.append(eoc("PF_PM_open", [
    m("pf_pm_n = 0"),
    {"u_location_variable": g("pf_pm_center")},
    # full run days 128-131: Janey's band camped just past 30 tiles, heard every day ("finished pulping the corpses") but never listed
    {"u_run_npc_eocs": ["PF_PM_scan_one"], "local": True, "npc_range": 60},  # day 150: a band in plain sight at 50 tiles wasn't listed (online range is 60)
    {"if": m("pf_pm_n == 0"),
     "then": [msg("No one is close enough to see.")],
     "else": [{
         "run_eoc_selector": [f"PF_PM_pick_{k}" for k in range(N)],
         "names": [g(f"pf_pm_label_{k}") for k in range(N)],
         "descriptions": [g(f"pf_pm_desc_{k}") for k in range(N)],
         "keys": [chr(ord('a') + k) for k in range(N)],
         "title": "People nearby (<global_val:pf_pm_n>)",
         "hide_failing": True,
         "allow_cancel": True}]},
], "Nearby screen.  Every NPC within 30 tiles writes itself into array slots pf_pm_*_<k> (names built at runtime, read back through the selector's variable-object names).  Works for vanilla NPCs too: they are addressed later by character id (u_set_talker), not by unique id."))

out.append(eoc("PF_PM_scan_one", [
    slotname("pf_pm_id_"),
    {"u_set_talker": {"var_val": "ref"}},
    {"u_location_variable": {"u_val": "pf_pm_here"}},
    m("pf_pm_tmp_dist = round(distance(pf_pm_center, u_pf_pm_here))"),
    {"if": m("value_or(u_pf_is_leader, -1) == 1"),
     "then": [{"set_string_var": "leads a band", "target_var": g("pf_pm_tmp_role")}],
     "else": [{"if": m("value_or(u_pf_is_leader, -1) == 0"),
               "then": [{"set_string_var": "travels with a band", "target_var": g("pf_pm_tmp_role")}],
               "else": [{"set_string_var": "a stranger", "target_var": g("pf_pm_tmp_role")}]}]},
    {"if": {"compare_string": [g("pf_pm_tmp_role"), "a stranger"]}, "then": [
        {"run_eocs": "PF_ID_ensure"},
        {"set_string_var": "AVATAR", "target_var": g("pf_m_other")},
        {"run_eocs": "PF_VIEW_read"},
        {"set_string_var": "<global_val:pf_read_tier_name>", "target_var": g("pf_pm_tmp_role"), "parse_tags": True}]},
    {"if": {"u_has_trait": "PF_CHILD"}, "then": [{"set_string_var": "a child", "target_var": g("pf_pm_tmp_role")}]},
    {"if": m("value_or(u_pf_orphaned, 0) == 1"), "then": [{"set_string_var": "a child, alone, hiding", "target_var": g("pf_pm_tmp_role")}]},
    # full run day 118: Creola, just named Creola Adcock and taken in as Dante's own, was still listed as "a child"
    {"if": {"and": [{"u_has_trait": "PF_CHILD"}, {"or": [{"compare_string": [{"u_val": "pf_guardian"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_mom"}, "AVATAR"]},
                                                        {"compare_string": [{"u_val": "pf_dad"}, "AVATAR"]}]}]},
     "then": [{"set_string_var": "your child", "target_var": g("pf_pm_tmp_role")}]},
    {"if": {"and": [m("value_or(u_pf_resident, 0) == 1"), {"not": {"u_has_trait": "PF_CHILD"}}]}, "then": [{"set_string_var": "lives with you", "target_var": g("pf_pm_tmp_role")}]},
    # KinfoldLab: Creola, Taunya and Lizeth Adcock grew up and read only "lives with you"
    {"if": {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, {"or": [{"compare_string": [{"u_val": "pf_guardian"}, "AVATAR"]}, {"compare_string": [{"u_val": "pf_mom"}, "AVATAR"]},
                                                              {"compare_string": [{"u_val": "pf_dad"}, "AVATAR"]}]}]},
     "then": [{"set_string_var": "your child, grown", "target_var": g("pf_pm_tmp_role")}]},
    # full run: NPC couples didn't show at all ("lives with you" for both halves of a marriage)
    {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"not": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}}, {"not": {"u_has_trait": "PF_CHILD"}}]}, "then": [
        {"set_string_var": "pf_name_<u_val:pf_sweet>", "target_var": {"context_val": "csn"}, "parse_tags": True},
        {"copy_var": {"var_val": "csn"}, "target_var": g("pf_pm_tmp_sw")},
        {"set_string_var": "with", "target_var": g("pf_pm_tmp_swr")},
        {"if": m("value_or(u_pf_rel_stage, 1) >= 3"), "then": [{"set_string_var": "married to", "target_var": g("pf_pm_tmp_swr")}]},
        {"set_string_var": "<global_val:pf_pm_tmp_role>, <global_val:pf_pm_tmp_swr> <global_val:pf_pm_tmp_sw>", "target_var": g("pf_pm_tmp_role"), "parse_tags": True}]},
    # full run day 88: Mariano, Dante's sweetheart, read only "lives with you"
    {"if": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}]}, "then": [
        {"set_string_var": "your sweetheart", "target_var": g("pf_pm_tmp_role")},
        {"if": m("value_or(u_pf_rel_stage, 1) == 2"), "then": [{"set_string_var": "your partner", "target_var": g("pf_pm_tmp_role")}]},
        {"if": {"and": [m("value_or(u_pf_rel_stage, 1) == 2"), m("value_or(u_pf_engaged, 0) == 1")]}, "then": [{"set_string_var": "engaged to you", "target_var": g("pf_pm_tmp_role")}]},
        {"if": m("value_or(u_pf_rel_stage, 1) >= 3"), "then": [{"set_string_var": "married to you", "target_var": g("pf_pm_tmp_role")}]}]},
    {"if": {"and": [{"u_has_effect": "PF_toddler"}, m("value_or(u_pf_follow, 0) == 2"), {"compare_string": [{"u_val": "pf_carrier"}, "AVATAR"]}]},
     "then": [{"set_string_var": "a toddler, holding your hand", "target_var": g("pf_pm_tmp_role")}]},
    {"if": {"u_has_effect": "PF_infant"}, "then": [{"set_string_var": "a baby", "target_var": g("pf_pm_tmp_role")},
        {"if": {"and": [m("value_or(u_pf_follow, 0) == 2"), {"compare_string": [{"u_val": "pf_carrier"}, "AVATAR"]}]},
         "then": [{"set_string_var": "a baby, in your arms", "target_var": g("pf_pm_tmp_role")}]}]},
    {"run_eocs": "PF_REG_name"},  # keep the directory name current (renames)
    slotname("pf_pm_label_"),
    {"set_string_var": "<u_name>  (<global_val:pf_pm_tmp_dist> tiles, <global_val:pf_pm_tmp_role>)", "target_var": {"var_val": "ref"}, "parse_tags": True},
    slotname("pf_pm_desc_"),
    {"set_string_var": "<u_name>.  What you can tell from here: <global_val:pf_pm_tmp_role>.", "target_var": {"var_val": "ref"}, "parse_tags": True},
    m("pf_pm_n += 1"),
], "u = one nearby NPC.  Takes the next free slot.", condition=m("pf_pm_n < %d" % N)))

for k in range(N):
    out.append(eoc(f"PF_PM_pick_{k}", [
        {"copy_var": g(f"pf_pm_id_{k}"), "target_var": g("pf_pm_sel_id")},
        {"copy_var": g(f"pf_pm_label_{k}"), "target_var": g("pf_pm_sel_label")},
        {"run_eocs": "PF_PM_person"},
    ], condition=m(f"pf_pm_n > {k}")))

out.append(eoc("PF_PM_person", [
    m("pf_pm_sel_adult = 0"),
    {"run_eocs": "PF_PM_sel_flags", "beta_talker": g("pf_pm_sel_id")},
    {
    "run_eoc_selector": ["PF_PM_act_talk", "PF_PM_act_tend", "PF_PM_act_meal", "PF_PM_act_call", "PF_PM_act_fire", "PF_PM_act_supply", "PF_PM_act_flirt", "PF_PM_act_confess", "PF_PM_act_marry", "PF_PM_act_end", "PF_PM_act_takein", "PF_PM_act_stepadopt", "PF_PM_act_pickup", "PF_PM_act_setdown", "PF_PM_act_hand", "PF_PM_act_letgo", "PF_PM_act_teach", "PF_PM_act_invite", "PF_PM_act_role", "PF_PM_act_info", "PF_PM_moments_shown"],
    "names": ["Talk", "Tend their wounds", "Share a meal with them", "Call them over", "Ask them to sit by the fire", "Bring their people supplies", "Flirt", "Tell them how you feel", "Ask them to marry you", "End it", "Take them in", "Raise them as your own", "Pick them up", "Set them down", "Take their hand", "Let go of their hand", "Teach them something", "Ask them to come live with you", "Ask them to take a different job", "What do I know about them?", "Moments (lab)"],
    "descriptions": [
        "Start a conversation.",
        "Kneel beside them with a rag and some clean water: stop the bleeding, clean the bites, wrap what's torn.  They come over if they can walk (a baby you go to), and nothing hostile can be close.",
        "Sit down together and eat (you need some food on you).  Once a day with each person: the surest way to get to know someone.",
        "Wave them over.  They walk to your side.",
        "They walk to the nearest fire within 40 tiles and settle there.",
        "Six things to eat for their band: from the stores near home, or a sack you packed (Home: Pack a sack of supplies).  Every few days.  Generosity is remembered.",
        "See if it lands.  That depends on them: who they're drawn to, and how they already feel about you.",
        "Say it.  They'll answer from their own heart.",
        "You've been together a while.  Ask.",
        "Tell them it's over.",
        "They have nobody.  They can stay with you.",
        "Your partner's child.  Make them yours too: one family, one name.",
        "Carry them with you.  Wherever you go, they go (4 kg of your carry weight).",
        "Hand them back to their mother, or set them down here.",
        "Little legs.  They stay at your side until you let go.",
        "They go back to following their family.",
        "Show them something you know better than they do.  Once a day.",
        "Home has room.  They'll answer from their own heart; if they travel with a band, the whole band comes.",
        "Cook, guard, forager, tinkerer, carer: the next one in line.",
        "How they seem to see you, how you see them, and what you've picked up about them.",
        "[lab] Make something happen between you and them, and watch the bond spine react."],
    "keys": ["t", "n", "a", "c", "f", "y", "r", "l", "p", "e", "h", "w", "u", "d", "o", "g", "s", "v", "b", "i", "m"],
    "title": "<global_val:pf_pm_sel_label>",
    "hide_failing": True,
    "allow_cancel": True}], "Person screen for the NPC whose character id is in pf_pm_sel_id.  Romance actions only exist for adults (never children; checked again inside)."))
out.append(eoc("PF_PM_sel_flags", [
    m("pf_pm_sel_adult = n_val('age') >= 18"),
    {"if": {"npc_has_trait": "PF_CHILD"}, "then": [m("pf_pm_sel_adult = 0")]},
    m("pf_pm_sel_mine = 0"), m("pf_pm_sel_stage = value_or(n_pf_rel_stage, 0)"),
    m("pf_pm_sel_orphan = 0"), m("pf_pm_sel_warm = (value_or(n_pf_v_AVATAR_w, 0) + value_or(n_pf_v_AVATAR_t, 0)) / 2 >= 10"),  # full run: warmth 10 alone still read "a stranger"; romance needs "someone they know"
    m("pf_pm_sel_baby = 0"), m("pf_pm_sel_held = 0"), m("pf_pm_sel_tod = 0"), m("pf_pm_sel_kid = 0"), m("pf_pm_sel_res = value_or(n_pf_resident, 0)"),
    # 2026-10-14: the action EOCs (call, fire) have no beta talker; reading n_pf_band there was an in-game error and a segfault
    m("pf_pm_sel_band = value_or(n_pf_band, 0) > 0"), m("pf_pm_sel_bandid = value_or(n_pf_band, 0)"),
    m("pf_pm_sel_supd = value_or(n_pf_supplied_day, -99)"),
    # day 151: Golly's newborn lay bleeding with her band 40-50 tiles off, and only NPCs could tend; you couldn't
    m("pf_pm_sel_hurt = 0"), {"if": N_HURT, "then": [m("pf_pm_sel_hurt = 1")]},
    {"set_string_var": "<npc_name>", "target_var": g("pf_pm_sel_name"), "parse_tags": True},
    {"npc_location_variable": g("pf_pm_sel_pos")}, {"u_location_variable": g("pf_pm_av_pos")},
    m("pf_pm_sel_dist = distance(pf_pm_sel_pos, pf_pm_av_pos)"),


    {"if": {"and": [{"npc_has_trait": "PF_CHILD"}, {"not": {"npc_has_effect": "PF_infant"}}]}, "then": [m("pf_pm_sel_kid = 1")]},
    {"if": {"npc_has_effect": "PF_toddler"}, "then": [m("pf_pm_sel_tod = 1"),
        {"if": {"and": [m("value_or(n_pf_follow, 0) == 2"), {"compare_string": [{"npc_val": "pf_carrier"}, "AVATAR"]}]}, "then": [m("pf_pm_sel_held = 1")]}]},
    {"if": {"npc_has_effect": "PF_infant"}, "then": [m("pf_pm_sel_baby = 1"),
        {"if": {"and": [m("value_or(n_pf_follow, 0) == 2"), {"compare_string": [{"npc_val": "pf_carrier"}, "AVATAR"]}]}, "then": [m("pf_pm_sel_held = 1")]}]},
    {"if": {"and": [{"npc_has_trait": "PF_CHILD"}, {"or": [m("value_or(n_pf_needs_home, 0) == 1"), m("value_or(n_pf_orphaned, 0) == 1")]},
                    {"or": [m("has_var(n_pf_guardian) == 0"), {"compare_string": [{"npc_val": "pf_guardian"}, "none"]}]}]},
     "then": [m("pf_pm_sel_orphan = 1")]},
    {"if": {"and": [m("value_or(n_pf_has_sweet, 0) == 1"), {"compare_string": [{"npc_val": "pf_sweet"}, "AVATAR"]}]}, "then": [m("pf_pm_sel_mine = 1")]},
    # full run day 118: Dante married Henriette, who had taken in Creola, but only an orphan with nobody could be taken in, so
    # the couple could never make her theirs.  Your partner's child (theirs, or one they took in) can be raised as your own.
    m("pf_pm_sel_step = 0"),
    {"if": {"and": [{"npc_has_trait": "PF_CHILD"}, m("value_or(u_pf_has_sweet, 0) == 1"), m("value_or(u_pf_rel_stage, 0) >= 2"),
                    {"not": {"compare_string": [{"npc_val": "pf_guardian"}, "AVATAR"]}},
                    {"or": [{"compare_string": [{"npc_val": "pf_guardian"}, {"u_val": "pf_sweet"}]}, {"compare_string": [{"npc_val": "pf_mom"}, {"u_val": "pf_sweet"}]},
                            {"compare_string": [{"npc_val": "pf_dad"}, {"u_val": "pf_sweet"}]}]}]},
     "then": [m("pf_pm_sel_step = 1")]},
    # full run day 124: Henriette died; her daughter Lakia stayed with Mitzi, and Dante, her widower, couldn't raise her.
    # Partners who died before pf_late_sweet was kept: the journal's wedding ("wed", you = 1) names them.  (KinfoldLab: the wedding
    # memory itself had been pushed out of Dante's 8 slots by the losses after it.)
] + [x for par in ["pf_mom", "pf_dad", "pf_guardian"] for x in [
    {"if": {"and": [m("has_var(u_pf_late_sweet) == 0"), m("value_or(u_pf_has_sweet, 0) == 0"), {"npc_has_trait": "PF_CHILD"}]}, "then": [
        {"set_string_var": f"pf_name_<npc_val:{par}>", "target_var": {"context_val": "lsn"}, "parse_tags": True},
        {"set_string_var": f"pf_reg_<npc_val:{par}>_dead", "target_var": {"context_val": "lsd"}, "parse_tags": True},
        {"set_string_var": "-", "target_var": g("pf_pm_ls_nm")}, {"copy_var": {"var_val": "lsn"}, "target_var": g("pf_pm_ls_nm")},
        {"if": m("value_or(v_lsd, 0) == 1"), "then": [
            {"if": {"and": [m(f"value_or(pf_ev_{e}_you, 0) == 1"), {"compare_string": [g(f"pf_ev_{e}_kind"), "wed"]},
                            {"compare_string": [g(f"pf_ev_{e}_youname"), g("pf_pm_ls_nm")]}]},
             "then": [{"copy_var": {"npc_val": par}, "target_var": {"u_val": "pf_late_sweet"}}]} for e in range(20)]}]}]] + [
    {"if": {"and": [{"npc_has_trait": "PF_CHILD"}, m("has_var(u_pf_late_sweet)"),
                    {"not": {"compare_string": [{"npc_val": "pf_guardian"}, "AVATAR"]}},
                    {"or": [{"compare_string": [{"npc_val": "pf_guardian"}, {"u_val": "pf_late_sweet"}]}, {"compare_string": [{"npc_val": "pf_mom"}, {"u_val": "pf_late_sweet"}]},
                            {"compare_string": [{"npc_val": "pf_dad"}, {"u_val": "pf_late_sweet"}]}]}]},
     "then": [m("pf_pm_sel_step = 1")]},
], "u = you, npc = the selected person."))
out.append(eoc("PF_PM_act_flirt", [{"run_eocs": "PF_ROM_flirt", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_flirt_no", "effect": [msg("Give it a little while before you try again.")]}]}],
    condition={"and": [m("pf_pm_sel_adult == 1"), m("value_or(pf_set_romance, 2) == 2"), m("pf_pm_sel_warm + pf_pm_sel_mine > 0")]}))
out.append(eoc("PF_PM_act_confess", [{"run_eocs": "PF_ROM_confess_you", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_adult == 1"), m("value_or(pf_set_romance, 2) == 2"), m("pf_pm_sel_mine == 0"), m("pf_pm_sel_warm == 1")]}))
out.append(eoc("PF_PM_act_marry", [{"run_eocs": "PF_HEART_you_propose", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_mine == 1"), m("pf_pm_sel_stage == 2")]}))
out.append(eoc("PF_PM_act_takein", [{"run_eocs": "PF_FAM_you_take_in", "beta_talker": g("pf_pm_sel_id")}],
    condition=m("pf_pm_sel_orphan == 1")))
out.append(eoc("PF_PM_act_stepadopt", [{"run_eocs": "PF_FAM_you_take_in", "beta_talker": g("pf_pm_sel_id")}],
    condition=m("value_or(pf_pm_sel_step, 0) == 1")))
out.append(eoc("PF_PM_act_pickup", [{"run_eocs": "PF_FAM_you_pick_up", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_baby == 1"), m("pf_pm_sel_held == 0")]}))
out.append(eoc("PF_PM_act_setdown", [{"run_eocs": "PF_FAM_you_set_down", "beta_talker": g("pf_pm_sel_id")}],
    condition=m("pf_pm_sel_held == 1")))
out.append(eoc("PF_PM_act_hand", [{"run_eocs": "PF_FAM_you_take_hand", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_tod == 1"), m("pf_pm_sel_held == 0")]}))
out.append(eoc("PF_PM_act_letgo", [{"run_eocs": "PF_FAM_you_let_go", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_tod == 1"), m("pf_pm_sel_held == 1")]}))
out.append(eoc("PF_PM_act_teach", [{"run_eocs": "PF_FAM_you_teach", "beta_talker": g("pf_pm_sel_id")}],
    condition=m("pf_pm_sel_kid == 1")))
out.append(eoc("PF_PM_act_invite", [{"run_eocs": "PF_HOME_invite", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_adult == 1"), m("pf_pm_sel_res == 0"), m("value_or(pf_home_set, 0) == 1")]}))
out.append(eoc("PF_PM_act_role", [{"run_eocs": "PF_HOME_role_next", "beta_talker": g("pf_pm_sel_id")}],
    condition={"and": [m("pf_pm_sel_adult == 1"), m("pf_pm_sel_res == 1")]}))
out.append(eoc("PF_PM_act_end", [{"run_eocs": "PF_HEART_you_end", "beta_talker": g("pf_pm_sel_id")}],
    condition=m("pf_pm_sel_mine == 1")))

def deal(used, n):
    """_p = a random line of n that the deck in `used` (a bitmask global) hasn't dealt yet; the deck refills once every line is out.
    Full run day 78: with only back-to-back repeats avoided, a band and the household got the same two lines the same morning."""
    # a fresh deck starts with the last line dealt already out (day 80: Lakia and then Creola, the same line across a refill)
    return ([{"if": m(f"value_or({used}, 0) >= {2 ** n - 1}"), "then": [m(f"{used} = 2 ^ value_or({used}_last, 0)")]}, m(f"_p = rand({n - 1})")]
            + [{"if": m(f"floor(value_or({used}, 0) / (2 ^ _p)) % 2 == 1"), "then": [m(f"_p = (_p + 1) % {n}")]} for _ in range(n - 1)]
            + [m(f"{used} = value_or({used}, 0) + 2 ^ _p"), m(f"{used}_last = _p")])

# playtest 3: a lone player had no way to get to know anyone except waiting; the concept's "share a meal" person action
# one portion of something edible: calories, a single unit (a stack counted by charges, like a pot of soup, can't be split
# off), and not rotten (engine patch 16; the stock exe has no such flag, so the check is skipped there)
MEAL_FOOD_OK = {"and": [m("n_calories() > 0"), m("n_val('count') == 1"),
                        {"or": [m("value_or(pf_eng_level, 0) < 16"), {"not": {"npc_has_flag": "PF_ROTTEN"}}]}]}
MEAL_READY = {"and": [MEAL_FOOD_OK, {"not": {"npc_has_flag": "RAW"}}]}
MEAL_LINES = ["You sit down with <npc_name> and split what you've got.  Neither of you says much, and that's fine.",
              "You eat with <npc_name>.  Somewhere in the middle of it they tell you where they were when it started.",
              "You and <npc_name> share what you have, passing it back and forth until it's gone.",  # full run: "out of the can" over a protein ration
              "<npc_name> eats with you, slowly, like someone who has learned not to waste a mouthful.",
              # full run: four meals with one band in a row repeated a line; more lines, and children get their own
              "You eat with <npc_name>.  They ask what you did before, and actually listen to the answer.",
              "<npc_name> eats with you and points out which roads are clear and which aren't.",
              "You and <npc_name> eat without talking, both of you watching the road.  It's still company."]
KID_MEAL_LINES = ["<npc_name> eats fast, watching you over the food like you might take it back.",
                  "You split your food with <npc_name>.  They save the last bite for later, just in case.",
                  "<npc_name> eats beside you and, halfway through, starts telling you about a dog they used to have.",
                  "<npc_name> takes the food with both hands and says thank you twice."]
out.append(eoc("PF_PM_act_meal", [{"run_eocs": "PF_PM_do_meal", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_meal", "effect": [msg("They're not here anymore.")]}]}],
    # full run: Meal vanished at home once your own pockets were empty, with the household's soup on the floor; at home the stores count
    condition={"and": [m("value_or(pf_pm_sel_baby, 0) == 0"),
                       {"or": [{"u_has_item_category": "food"},
                               m("(value_or(pf_home_set, 0) == 1) * (distance(pf_pm_center, pf_home_loc) <= 30) * (value_or(pf_residents_n, 0) > 0)")]}]}))
out.append(eoc("PF_PM_do_meal", [
    {"if": m("value_or(n_pf_meal_you_day, -1) == floor(time('now') / time('1 d'))"),
     "then": [msg("You've already eaten with <npc_name> today.")],
     # day 151 (the user): shared meals used no food and fed nobody.  A meal takes one thing to eat, carried first, else from
     # the stores at home; you get half of it (calories and vitamins), they get the rest.  Nothing to eat, no meal.
     "else": [m("pf_ml_ok = 0"), {"run_eocs": "PF_ENGINE_caps"},
              # day 159: "One raw potato, split two ways."  Something ready to eat first (yours, then the stores), raw food only if
              # that's all there is.
              # day 182: a week of meals at home ate the trail food in Dante's pack, and he walked out with nothing.  At home
              # the stores go first; your pack only when there's nothing there (or you're away).
              ] + [step for cond in (MEAL_READY, MEAL_FOOD_OK) for step in (
              {"if": m("(pf_ml_ok == 0) * (value_or(pf_home_set, 0) == 1) * (distance(pf_pm_center, pf_home_loc) <= 30) * has_var(pf_stores_loc)"),
               "then": [{"u_map_run_item_eocs": "random", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2,
                         "search_data": [{"category": "food", "condition": cond}], "true_eocs": ["PF_PM_meal_take"]}]},
              {"if": m("pf_ml_ok == 0"),
               "then": [{"u_run_inv_eocs": "random", "search_data": [{"category": "food", "condition": cond}], "true_eocs": ["PF_PM_meal_take"]}]})] + [
              {"if": m("pf_ml_ok == 0"), "then": [msg("You've nothing to eat to share with <npc_name>.")]}]},
    {"if": m("pf_ml_ok == 1"), "then": [
              m("n_pf_meal_you_day = floor(time('now') / time('1 d'))"),
              # full run: a meal with someone 6 tiles off read "you sit down with them"; they come and sit with you (and stay a while)
              {"run_eocs": "PF_PM_walk_to_center", "alpha_talker": "npc"},
              # full run day 124: "Janey Hammond eats with you" from 27 tiles away; say that they come over
              {"if": m("distance(pf_pm_center, 'npc') > 6"), "then": [msg("You hold up the food, and <npc_name> comes over to share it.")]},
              {"if": {"npc_has_trait": "PF_CHILD"},
               "then": deal("pf_kmeal_used", len(KID_MEAL_LINES)) + [{"if": m(f"_p == {i}"), "then": [msg(t)]} for i, t in enumerate(KID_MEAL_LINES)],
               "else": deal("pf_meal_used", len(MEAL_LINES)) + [{"if": m(f"_p == {i}"), "then": [msg(t)]} for i, t in enumerate(MEAL_LINES)]}] + [
              m("pf_m_str_in = 45"), {"run_eocs": "PF_MK_meal_shared", "beta_talker": "npc"},
              m("pf_meals_you_total = value_or(pf_meals_you_total, 0) + 1"),
              # full run day 86: a week of meals with a band and no sign anything was changing before the yes; say when it does
              m("pf_court_say = 0"), {"run_eocs": "PF_PM_court_read", "alpha_talker": "npc"},
              {"if": m("pf_court_say == 1"), "then": [msg("<npc_name> has started keeping a place for you when you sit down.  They're warming to you.", "good")]},
              {"if": m("pf_court_say == 2"), "then": [msg("<npc_name> lingers after the meal and asks, as if it doesn't matter, how many people live at your place.  Ask them now and they might say yes.", "good")]},
              msg("One <global_val:pf_ml_food>, split two ways.")]},
], "Alpha = you, beta = the person.  Once a day with each person: a meal_shared moment between you (both views).  It uses one thing to eat (yours, else the stores at home) and you get half of it."))
out.append(eoc("PF_PM_meal_take", [
    {"set_string_var": "<npc_name>", "target_var": g("pf_ml_food"), "parse_tags": True},
    {"run_eocs": "PF_ENGINE_eat_share"},
    m("pf_ml_ok = 1"),
    "npc_die",
], "u = you, npc = one thing to eat (one portion: a solid food item, or a liquid of one serving).  Half of it is yours; the item is used up."))
# day 160: the half went straight into the body (no stomach: "Hungry" after the meal, "Consumed today: 0 kcal").  The People
# First Engine mod overrides this with engine patch 23 (u_pf_eat_share() = 50: half the food into your stomach, eaten for real).
out.append(eoc("PF_ENGINE_eat_share", [
    m("u_calories() = u_calories() + n_calories() / 2"),
] + [m(f"u_vitamin('{v}') = u_vitamin('{v}') + n_vitamin('{v}') / 2") for v in ("calcium", "iron", "vitC")],
    "Stock build: u = the eater, npc = the food.  Half its calories and vitamins straight into the body."))
out.append(eoc("PF_PM_court_read", [
    {"run_eocs": "PF_ID_ensure"},
    {"set_string_var": "AVATAR", "target_var": g("pf_m_other")},
    {"run_eocs": "PF_VIEW_read"},
    # the steps of the invitation answer (gen_home PF_HOME_invite): warming at warmth 20, a yes at 35/25 or 50/15
    m("_cs = (pf_read_w >= 20) + ((pf_read_w >= 35) * (pf_read_t >= 25) + (pf_read_w >= 50) * (pf_read_t >= 15) > 0)"),
    {"if": m("_cs > value_or(u_pf_court_stage, 0)"), "then": [m("u_pf_court_stage = _cs"), m("pf_court_say = _cs")]},
], "u = someone you just ate with (not living with you, not a child).  pf_court_say = the courting step they just reached (1 warming, 2 ready to say yes), or 0.",
    condition={"and": [m("value_or(u_pf_resident, 0) == 0"), {"not": {"u_has_trait": "PF_CHILD"}}]}))
out.append(eoc("PF_PM_act_tend", [
    # a baby has to be reached; anyone who can walk comes over (like a meal) from up to 20 tiles
    m("pf_pm_sel_near = (pf_pm_sel_dist <= 3) + (pf_pm_sel_dist <= 20) * (pf_pm_sel_baby == 0) > 0"),
    # day 153: n_monsters_nearby's "hostile" means "not a pet", so a neutral animal (or one behind a wall) blocked tending a
    # baby in the middle of the house.  The mod's calm check: hostiles you can see, anything within 3, hostile people.
    {"run_eocs": "PF_THREAT_scan"}, m("pf_pm_sel_calm = pf_threat == 0"),
    {"if": m("pf_pm_sel_near == 0"), "then": [msg("You'd need to be right beside them.")],
     "else": [{"if": m("pf_pm_sel_calm == 0"), "then": [msg("Not with the dead this close.  Deal with them first.", "bad")],
               "else": [{"if": m("pf_pm_sel_dist > 3"), "then": [
                            {"run_eocs": "PF_PM_walk_to_center", "alpha_talker": g("pf_pm_sel_id")},
                            msg("You wave <global_val:pf_pm_sel_name> over and sit them down.")]},
                        {"run_eocs": "PF_PM_do_tend", "beta_talker": g("pf_pm_sel_id"),
                         "false_eocs": [{"id": "PF_PM_gone_tend", "effect": [msg("They're not here anymore.")]}]}]}]},
], condition=m("value_or(pf_pm_sel_hurt, 0) == 1")))
out.append(eoc("PF_PM_do_tend", [
] + [m(f"n_hp('{bp}') = min(n_hp('{bp}') + 8, n_hp_max('{bp}'))") for bp in HP_PARTS] + [
    {"npc_lose_effect": "bleed", "target_part": "ALL"}, {"npc_lose_effect": "bite", "target_part": "ALL"},
    m("n_pf_tended_t = time('now')"),
    {"if": {"npc_has_effect": "PF_infant"},
     "then": [msg("You clean <npc_name>'s cuts and wrap them tight.  They scream the whole time, which is a good sign.", "good")],
     "else": [{"if": {"npc_has_trait": "PF_CHILD"},
               "then": [msg("You kneel beside <npc_name> with a rag and some clean water.  \"Hold still.\"  They hold still, mostly.", "good")],
               "else": [msg("You kneel beside <npc_name> with a rag and some clean water, clean the wounds and wrap what's torn.", "good")]}]},
    m("pf_m_str_in = 60"), {"run_eocs": "PF_MK_care_given"},
    m("pf_tended_total = value_or(pf_tended_total, 0) + 1"),
], "Alpha = you, beta = the wounded person.  Same as a carer's tending (PF_RK_tend_do): a little hp back on every main part, bleeding stopped, bites cleaned; care from you (60)."))
out.append(eoc("PF_PM_act_talk", [{"run_eocs": "PF_PM_do_talk", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_talk", "effect": [msg("They're not here anymore.")]}]}]))
out.append(eoc("PF_PM_do_talk", [{"open_dialogue": {"topic": ""}}], "An empty topic makes open_dialogue talk to the beta talker; a non-object value is never read and counts as a JSON error."))

out.append(eoc("PF_PM_act_call", [
    {"u_location_variable": g("pf_pm_center")},
    # full run day 151: Taunya (a child) had fled a skeletal dog 58 tiles from home; "Call them over" sent her running back
    # alone across open ground, into the zombie dogs at the gate, and she died there.  A child far off, or with the dead
    # close to them, isn't called: you go and get them.
    m("pf_cl_ok = 1"),
    {"run_eocs": "PF_PM_call_check", "alpha_talker": g("pf_pm_sel_id"),
     "false_eocs": [{"id": "PF_PM_gone_call", "effect": [m("pf_cl_ok = 0"), msg("They're not here anymore.")]}]},
    {"if": m("pf_cl_ok == 2"), "then": [msg("<global_val:pf_cl_name> is too far off to hear you, and you won't call a child across open ground alone.  Go and get them.", "bad")]},
    {"if": m("pf_cl_ok == 3"), "then": [msg("The dead are too close to <global_val:pf_cl_name>.  If you call, they'll come running straight past them.  Go and get them.", "bad")]},
    {"if": m("pf_cl_ok == 1"), "then": [{"run_eocs": "PF_PM_walk_to_center", "alpha_talker": g("pf_pm_sel_id")}]},
    # full run day 124: Janey Hammond (leading a band) came 2 tiles in half an hour; her band's own walk orders won.  Since then
    # a wave holds them (and a leader's whole band) for 30 minutes, so "they stay with their people" was wrong (day 150).
    {"if": m("pf_cl_ok == 1"), "then": [
        {"if": {"and": [m("pf_pm_sel_band == 1"), m("value_or(pf_pm_sel_res, 0) == 0")]},
         "then": [msg("You wave them over.  They wave back and come over for a bit.")],
         "else": [msg("You wave them over.")]}]},
], condition=m("value_or(pf_pm_sel_baby, 0) == 0")))
out.append(eoc("PF_PM_call_check", [
    {"set_string_var": "<u_name>", "target_var": g("pf_cl_name"), "parse_tags": True},
    {"u_location_variable": {"u_val": "pf_pos"}},
    {"if": m("distance(u_pf_pos, pf_pm_center) > 30"), "then": [m("pf_cl_ok = 2")],
     "else": [{"if": m("u_monsters_nearby('radius': 10, 'attitude': 'hostile') > 0"), "then": [m("pf_cl_ok = 3")]}]},
], "u = the person you'd call.  For a child: pf_cl_ok 2 if farther than 30 tiles, 3 if anything hostile is within 10 of them.",
    condition={"u_has_trait": "PF_CHILD"}))
out.append(eoc("PF_PM_walk_to_center", [
    m("u_pf_wave_until = time('now') + time('30 m')"),  # full run: a band leader's own walk overrode the wave; the band holds (alife.json, band.json)
    {"copy_var": g("pf_pm_center"), "target_var": {"u_val": "pf_walk_to"}},
    {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": 1},
    {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
]))

# full run day 138: Kinfold's evenings happen at home with no fire, so "sit by the fire" only ever said there was none.
# With no fire lit, home is where people sit of an evening; a band member stays with their band (as with "Call them over").
FIRE_BAND = m("pf_pm_fire_band == 1")
out.append(eoc("PF_PM_act_fire", [
    m("pf_pm_fire_band = (pf_pm_sel_band == 1) * (value_or(pf_pm_sel_res, 0) == 0)"),
    {"u_location_variable": g("pf_pm_fire"), "field": "fd_fire", "target_max_radius": 40,
     "true_eocs": [{"id": "PF_PM_fire_found", "effect": [
         {"run_eocs": "PF_PM_walk_to_fire", "alpha_talker": g("pf_pm_sel_id")},
         {"if": FIRE_BAND, "then": [msg("You point them to the fire.  They nod, but they stay with their people.")],
          "else": [msg("They head for the fire.")]}]}],
     "false_eocs": [{"id": "PF_PM_fire_none", "effect": [
         {"u_location_variable": g("pf_pm_center")},
         {"if": {"and": [m("value_or(pf_home_set, 0) == 1"), m("distance(pf_pm_center, pf_home_loc) <= 40")]}, "then": [
             {"copy_var": g("pf_home_loc"), "target_var": g("pf_pm_fire")},
             {"run_eocs": "PF_PM_walk_to_fire", "alpha_talker": g("pf_pm_sel_id")},
             {"if": FIRE_BAND, "then": [msg("No fire is lit, so you ask them to come and sit with your people at home.  They nod, but they stay with their own.")],
              "else": [msg("No fire is lit, so you ask them to come and sit with your people at home.  They head over.")]}],
          "else": [msg("There's no fire burning within 40 tiles.")]}]}]},
], condition=m("value_or(pf_pm_sel_baby, 0) == 0")))
out.append(eoc("PF_PM_walk_to_fire", [
    {"copy_var": g("pf_pm_fire"), "target_var": {"u_val": "pf_walk_to"}},
    {"location_variable_adjust": {"u_val": "pf_walk_to"}, "x_adjust": m("rand(2) - 1"), "y_adjust": 1},
    {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
], "Sits them one tile south of the fire (plus or minus one east-west), not in it."))

# full run day 145: a band was won by shared meals alone at about +1 warmth a day (warmth decays 0.33 a day): three to
# four weeks of the same day.  A generous act that costs the household something: a sack of real food from the stores
# for the whole band, a care moment (strength 60) from you to each of them.  Once every 3 days per band.
TODAY_P = "floor(time('now') / time('1 d'))"
out.append(eoc("PF_PM_act_supply", [
    {"if": m(f"{TODAY_P} - pf_pm_sel_supd < 3"), "then": [msg("You brought them supplies only a day or two ago.  Give it a few days.")], "else": [
        {"run_eocs": "PF_STORES_count"},
        # day 150: away from home, a sack packed at home (Home: Pack a sack of supplies) does instead
        m("pf_sp_src = 0"),
        {"if": m("pf_dr_real >= 12"), "then": [m("pf_sp_src = 1")],
         "else": [{"if": {"u_has_items": {"item": "PF_supply_sack", "count": 1}}, "then": [m("pf_sp_src = 2")]}]},
        {"if": m("pf_sp_src == 0"), "then": [msg("You've nothing to bring them.  Near home the stores do (a dozen things to eat there); away from home, pack a sack first (Home: Pack a sack of supplies).")], "else": [
            {"if": m("pf_sp_src == 1"), "then": [
                m("pf_sp_took = 0"),
                {"u_map_run_item_eocs": "all", "loc": g("pf_stores_loc"), "min_radius": 0, "max_radius": 2, "search_data": [{"category": ["food"]}],
                 "true_eocs": [{"id": "PF_PM_supply_take", "effect": [{"if": m("pf_sp_took < 6"), "then": [m("pf_sp_took += 1"), "npc_die"]}]}]}],
             "else": [{"u_consume_item": "PF_supply_sack", "count": 1}]},
            {"run_eocs": {"id": "PF_PM_supply_name", "effect": [{"set_string_var": "<u_name>", "target_var": g("pf_sp_who"), "parse_tags": True}]},
             "alpha_talker": g("pf_pm_sel_id")},
            m("pf_sp_n = 0"),
            {"u_run_npc_eocs": [{"id": "PF_PM_supply_one",
                                 "condition": {"and": [m("value_or(u_pf_band, 0) == pf_pm_sel_bandid"), m("value_or(u_pf_resident, 0) == 0")]},
                                 "effect": [m(f"u_pf_supplied_day = {TODAY_P}"), m("pf_sp_n += 1"),
                                            {"u_set_talker": g("pf_sp_t")},
                                            m("pf_m_str_in = 60"), {"run_eocs": "PF_MK_care_given", "alpha_talker": "avatar", "beta_talker": g("pf_sp_t")}]}],
             "local": True, "npc_range": 60},
            {"if": m("pf_sp_src == 1"), "then": [msg("You fill a sack from the stores and carry it out to <global_val:pf_sp_who>'s people.  <global_val:pf_sp_who> looks at it for a long moment before taking it.")],
             "else": [msg("You hand <global_val:pf_sp_who> the sack you've carried all this way.  <global_val:pf_sp_who> opens it, looks at you, and doesn't say anything for a moment.")]},
            m("pf_supplies_given_total = value_or(pf_supplies_given_total, 0) + 1")]}]},
], condition={"and": [m("value_or(pf_pm_sel_baby, 0) == 0"), m("pf_pm_sel_band == 1"), m("value_or(pf_pm_sel_res, 0) == 0"), m("value_or(pf_pm_sel_adult, 0) == 1")]}))
out.append(eoc("PF_PM_act_info", [{"run_eocs": "PF_PM_show_info", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_info", "effect": [msg("They're not here anymore.")]}]}]))
out.append(eoc("PF_PM_show_info", [
    {"run_eocs": "PF_PM_info_npc_side", "alpha_talker": "npc"},
    {"copy_var": {"npc_val": "pf_uid"}, "target_var": g("pf_m_other")},
    {"run_eocs": "PF_VIEW_read"},
    m("pf_show_my_w = round(pf_read_w)"), m("pf_show_my_t = round(pf_read_t)"), m("pf_show_my_x = round(pf_read_x)"),
    {"copy_var": g("pf_read_tier_name"), "target_var": g("pf_show_my_tier")}, m("pf_show_my_tn = pf_read_tier"),
    {"switch": m("pf_show_their_tn"), "cases": [{"case": i, "effect": {"set_string_var": t, "target_var": g("pf_show_their_ph")}} for i, t in enumerate(
        ["a stranger", "someone they know", "a companion", "someone close", "someone they'd die for"])]},
    {"switch": m("pf_show_my_tn"), "cases": [{"case": i, "effect": {"set_string_var": t, "target_var": g("pf_show_my_ph")}} for i, t in enumerate(
        ["a stranger", "someone you know", "a companion", "someone close", "someone you'd die for"])]},
    {"if": m("value_or(pf_set_labs, 0) == 0"), "then": [
        {"if": m("pf_show_my_w >= 30"),
         "then": [msg("<npc_name> seems to see you as <global_val:pf_show_their_ph>.  To you, they're <global_val:pf_show_my_ph>.  By now you'd say they're <global_val:pf_show_temper> (<global_val:pf_show_quirk>).")],
         "else": [msg("<npc_name> seems to see you as <global_val:pf_show_their_ph>.  To you, they're <global_val:pf_show_my_ph>.  You don't know them well enough yet to say what they're like.")]}],
     "else": [msg("[debug] <npc_name> (<global_val:pf_show_temper>, <global_val:pf_show_quirk>) sees you as <global_val:pf_show_their_tier>: warmth <global_val:pf_show_their_w>, trust <global_val:pf_show_their_t>, tension <global_val:pf_show_their_x>.  You see them as <global_val:pf_show_my_tier>: warmth <global_val:pf_show_my_w>, trust <global_val:pf_show_my_t>, tension <global_val:pf_show_my_x>.  They hold <global_val:pf_show_mem_n> memories; the latest: <global_val:pf_show_mem_kind>.  Romance: <global_val:pf_show_rom>, <global_val:pf_show_open>; attraction to you <global_val:pf_show_a>; <global_val:pf_show_stage>: <global_val:pf_show_sweet>.")]},
], "Alpha = avatar, beta = the NPC.  What a player sees is in words, from their own point of view; the numbers only with the test labs shown."))
out.append(eoc("PF_PM_moments_shown", [{"run_eocs": "PF_PM_moments"}], "The moments lab, only with Settings: test labs shown.", condition=m("value_or(pf_set_labs, 0) == 1")))
out.append(eoc("PF_PM_info_npc_side", [
    {"run_eocs": "PF_ID_ensure"},
    {"set_string_var": "AVATAR", "target_var": g("pf_m_other")},
    {"run_eocs": "PF_VIEW_read"},
    m("pf_show_their_w = round(pf_read_w)"), m("pf_show_their_t = round(pf_read_t)"), m("pf_show_their_x = round(pf_read_x)"),
    {"copy_var": g("pf_read_tier_name"), "target_var": g("pf_show_their_tier")}, m("pf_show_their_tn = pf_read_tier"),
    {"set_string_var": "even-tempered", "target_var": g("pf_show_temper")},
    {"if": {"u_has_trait": "PF_T_SOCIABLE"}, "then": [{"set_string_var": "sociable", "target_var": g("pf_show_temper")}]},
    {"if": {"u_has_trait": "PF_T_LONER"}, "then": [{"set_string_var": "a loner", "target_var": g("pf_show_temper")}]},
    {"set_string_var": "no quirk", "target_var": g("pf_show_quirk")},
    {"if": {"u_has_trait": "PF_Q_LOYAL"}, "then": [{"set_string_var": "loyal to a fault", "target_var": g("pf_show_quirk")}]},
    {"if": {"u_has_trait": "PF_Q_HATES_WASTE"}, "then": [{"set_string_var": "hates waste", "target_var": g("pf_show_quirk")}]},
    {"if": {"u_has_trait": "PF_Q_MOTHER_HEN"}, "then": [{"set_string_var": "a mother hen", "target_var": g("pf_show_quirk")}]},
    {"if": {"u_has_trait": "PF_Q_GALLOWS"}, "then": [{"set_string_var": "gallows humor", "target_var": g("pf_show_quirk")}]},
    {"if": {"u_has_trait": "PF_Q_PROUD"}, "then": [{"set_string_var": "proud", "target_var": g("pf_show_quirk")}]},
    m("pf_show_a = round(pf_read_a)"),
    {"set_string_var": "not romantic", "target_var": g("pf_show_rom")},
    {"if": m("value_or(u_pf_rom, 0) == 1"), "then": [
        {"switch": m("u_pf_orient"), "cases": [
            {"case": 0, "effect": {"set_string_var": "drawn to women", "target_var": g("pf_show_rom")}},
            {"case": 1, "effect": {"set_string_var": "drawn to men", "target_var": g("pf_show_rom")}},
            {"case": 2, "effect": {"set_string_var": "drawn to anyone", "target_var": g("pf_show_rom")}}]}]},
    {"if": m("value_or(u_pf_adult, 0) == 0"), "then": [{"set_string_var": "a child: never part of romance", "target_var": g("pf_show_rom")}]},
    {"set_string_var": "set in their feelings", "target_var": g("pf_show_open")},
    {"if": m("value_or(u_pf_open, 0) >= 0.5"), "then": [{"set_string_var": "can warm up", "target_var": g("pf_show_open")}]},
    {"if": m("value_or(u_pf_open, 0) >= 0.9"), "then": [{"set_string_var": "easily swayed", "target_var": g("pf_show_open")}]},
    {"set_string_var": "nobody", "target_var": g("pf_show_sweet")},
    {"switch": m("value_or(u_pf_rel_stage, 0)"), "cases": [
        {"case": 0, "effect": {"set_string_var": "sweetheart", "target_var": g("pf_show_stage")}},
        {"case": 1, "effect": {"set_string_var": "sweetheart", "target_var": g("pf_show_stage")}},
        {"case": 2, "effect": {"set_string_var": "partner", "target_var": g("pf_show_stage")}},
        {"case": 3, "effect": {"set_string_var": "spouse", "target_var": g("pf_show_stage")}}]},
    {"if": m("value_or(u_pf_has_sweet, 0) == 1"), "then": [
        {"set_string_var": "pf_name_<u_val:pf_sweet>", "target_var": {"context_val": "sn"}, "parse_tags": True},
        {"copy_var": {"var_val": "sn"}, "target_var": g("pf_show_sweet")},
        {"if": {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}, "then": [{"set_string_var": "you", "target_var": g("pf_show_sweet")}]}]},
    m("pf_show_mem_n = value_or(u_pf_mem_count, 0)"),
    {"set_string_var": "none", "target_var": g("pf_show_mem_kind")},
    {"if": m("pf_show_mem_n > 0"), "then": [
        m("u_pf_tmp_last = (value_or(u_pf_mem_next, 0) + 7) % 8"),
        {"set_string_var": "u_pf_mem_<u_val:pf_tmp_last>_kind", "target_var": {"context_val": "lk"}, "parse_tags": True},
        {"copy_var": {"var_val": "lk"}, "target_var": g("pf_show_mem_kind")}]},
], "u = the NPC.  Reads their view of the avatar and their personality into pf_show_* globals."))
out.append(eoc("PF_PM_moments", [{
    "run_eoc_selector": ["PF_PM_mk_meal_shared", "PF_PM_mk_care_given", "PF_PM_mk_gift", "PF_PM_mk_saved_life", "PF_PM_mk_shared_danger", "PF_PM_mk_watch_covered", "PF_PM_mk_argument", "PF_PM_mk_insult", "PF_PM_mk_wasted_food", "PF_PM_mk_betrayal", "PF_PM_age_60"],
    "names": ["Share a meal", "Tend to them (care)", "Give them a gift", "Save their life", "Face danger together", "Cover their watch", "Argue with them", "Insult them", "Waste food in front of them", "Betray them", "[test] 60 days pass without contact"],
    "keys": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
    "title": "[lab] What happens between you and <global_val:pf_pm_sel_label>?",
    "allow_cancel": True}]))
out.append(eoc("PF_PM_mk_meal_shared", [{"run_eocs": "PF_MK_meal_shared", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_meal_shared_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_care_given", [{"run_eocs": "PF_MK_care_given", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_care_given_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_gift", [{"run_eocs": "PF_MK_gift", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_gift_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_saved_life", [{"run_eocs": "PF_MK_saved_life", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_saved_life_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_shared_danger", [{"run_eocs": "PF_MK_shared_danger", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_shared_danger_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_watch_covered", [{"run_eocs": "PF_MK_watch_covered", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_watch_covered_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_argument", [{"run_eocs": "PF_MK_argument", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_argument_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_insult", [{"run_eocs": "PF_MK_insult", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_insult_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_wasted_food", [{"run_eocs": "PF_MK_wasted_food", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_wasted_food_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_mk_betrayal", [{"run_eocs": "PF_MK_betrayal", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_mk_betrayal_gone", "effect": [msg("They're not here anymore.")]}]}, {"run_eocs": "PF_PM_act_info"}]))
out.append(eoc("PF_PM_age_60", [{"run_eocs": "PF_PM_age_60_npc", "beta_talker": g("pf_pm_sel_id")}, {"run_eocs": "PF_PM_act_info"}],
    "[test] Ages the selected person's view of you by 60 days, to check lazy decay and its floor without waiting months."))
out.append(eoc("PF_PM_age_60_npc", [{"run_eocs": "PF_PM_age_60_view", "alpha_talker": "npc"}]))
out.append(eoc("PF_PM_age_60_view", [
    {"set_string_var": "AVATAR", "target_var": g("pf_m_other")},
    {"set_string_var": "u_pf_v_<global_val:pf_m_other>_l", "target_var": {"context_val": "rl"}, "parse_tags": True},
    {"if": m("value_or(v_rl, -1) >= 0"), "then": [m("v_rl = v_rl - time('60 d')")]}]))
# ---------------------------------------------------------------- settings (concept §6.2 screen 6)
def setname(var, default, cases, target):
    return {"switch": m(f"value_or({var}, {default})"), "cases": [{"case": k, "effect": {"set_string_var": v, "target_var": g(target)}} for k, v in cases]}
out.append(eoc("PF_SET_open", [
    setname("pf_set_romance", 2, [(0, "Romance: off"), (1, "Romance: between NPCs only"), (2, "Romance: on (people may fall for you, and you for them)")], "pf_set_l_rom"),
    setname("pf_set_chatter", 1, [(0, "Chatter: quiet (no activity narration or glances at the fire)"), (1, "Chatter: normal")], "pf_set_l_chat"),
    setname("pf_alife_on", 1, [(0, "A-Life simulation: paused"), (1, "A-Life simulation: running")], "pf_set_l_alife"),
    setname("pf_set_bands", 8, [(0, "People in the world: none (only those you meet some other way)"), (4, "People in the world: few (up to 4 bands)"),
                                (8, "People in the world: some (up to 8 bands)"), (16, "People in the world: many (up to 16 bands)")], "pf_set_l_bands"),
    {"set_string_var": "People each person keeps track of: <global_val:pf_known_cap>", "target_var": g("pf_set_l_known"), "parse_tags": True},
    setname("pf_set_jealousy", 1, [(0, "Jealousy and breakups: off"), (1, "Jealousy and breakups: on")], "pf_set_l_jeal"),
    setname("pf_set_preg", 1, [(0, "Pregnancy: off"), (1, "Pregnancy: on")], "pf_set_l_preg"),
    setname("pf_set_grow", 1, [(0, "Growing up: realistic (9-month pregnancy, 18 years to adulthood)"), (1, "Growing up: accelerated (a month's pregnancy, a year of childhood per month)"), (2, "Growing up: fast (for testing)")], "pf_set_l_grow"),
    setname("pf_horn_on", 1, [(0, "The Horn (camp alarm): off"), (1, "The Horn (camp alarm): on")], "pf_set_l_horn"),
    setname("pf_set_defend", 1, [(0, "Standing up for each other: off"), (1, "Standing up for each other: on (engine build)")], "pf_set_l_defend"),
    setname("pf_set_labs", 0, [(0, "Test labs and debug log: hidden"), (1, "Test labs and debug log: shown")], "pf_set_l_labs"),
    {"run_eoc_selector": ["PF_SET_rom", "PF_SET_chat", "PF_SET_alife", "PF_SET_bands", "PF_SET_known", "PF_SET_jeal", "PF_SET_preg", "PF_SET_grow", "PF_SET_horn", "PF_SET_defend", "PF_SET_labs"],
     "names": [g("pf_set_l_rom"), g("pf_set_l_chat"), g("pf_set_l_alife"), g("pf_set_l_bands"), g("pf_set_l_known"), g("pf_set_l_jeal"), g("pf_set_l_preg"), g("pf_set_l_grow"), g("pf_set_l_horn"), g("pf_set_l_defend"), g("pf_set_l_labs")],
     "descriptions": ["Cycles on, between NPCs only, and off.  Off stops new attraction from turning into glances or confessions (bonds keep their values).",
                      "Quiet keeps the evenings' bonds but drops the narration lines about what people are doing.",
                      "The off-screen world: bands traveling, hunting and camping while you're away.",
                      "How many bands live in the world around you.  New ones turn up at the edge of what you can see, every few hours, until there are this many.",
                      "Dunbar's layers: 15 (close circle), 50 (friends), 150 (everyone you know).  More costs save size, not CPU.",
                      "Whether a glance can make someone jealous, and whether couples can fall apart.",
                      "Whether partners (adults, never children) can have children.",
                      "How fast pregnancy and childhood go.  Few runs last 18 game years, so accelerated is the default.",
                      "When something hostile comes close, someone raises the alarm, children are taken away and adults go to meet it.",
                      "People fight for those they're bonded to (family, partner, band, household, close friends, you if they like you enough).  Needs the People First engine build; on the official game it does nothing.",
                      "For testing the mod: shows the lab menus in the People First menu and the A-Life debug line in the message log."],
     "keys": ["r", "c", "a", "b", "k", "j", "p", "g", "h", "d", "t"], "title": "People First settings", "allow_cancel": True}],
    "Settings screen.  Each choice cycles a value and reopens the screen."))
out.append(eoc("PF_SET_rom", [m("pf_set_romance = (value_or(pf_set_romance, 2) + 2) % 3"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_chat", [m("pf_set_chatter = 1 - value_or(pf_set_chatter, 1)"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_alife", [m("pf_alife_on = 1 - value_or(pf_alife_on, 1)"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_bands", [m("pf_set_bands = value_or(pf_set_bands, 8) >= 16 ? 0 : (value_or(pf_set_bands, 8) == 0 ? 4 : value_or(pf_set_bands, 8) * 2)"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_jeal", [m("pf_set_jealousy = 1 - value_or(pf_set_jealousy, 1)"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_preg", [m("pf_set_preg = 1 - value_or(pf_set_preg, 1)"), {"run_eocs": "PF_SET_open"}]))
# 2026-10-15: the switch keeps every child's age and every pregnancy's progress (gen_family PF_FAM_repace)
out.append(eoc("PF_SET_grow", [m("pf_pace_old = (value_or(pf_set_grow, 1) == 0 ? 1 : (value_or(pf_set_grow, 1) == 1 ? 12 : 120))"), m("pf_term_old = (value_or(pf_set_grow, 1) == 0 ? 270 : (value_or(pf_set_grow, 1) == 1 ? 30 : 3))"),
                               m("pf_set_grow = (value_or(pf_set_grow, 1) + 1) % 3"), {"run_eocs": "PF_FAM_repace"}, {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_horn", [m("pf_horn_on = 1 - value_or(pf_horn_on, 1)"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_defend", [m("pf_set_defend = 1 - value_or(pf_set_defend, 1)"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_labs", [m("pf_set_labs = 1 - value_or(pf_set_labs, 0)"), m("pf_debug = pf_set_labs"), {"run_eocs": "PF_SET_open"}]))
out.append(eoc("PF_SET_known", [m("pf_known_cap = pf_known_cap < 50 ? 50 : (pf_known_cap < 150 ? 150 : 15)"), {"run_eocs": "PF_SET_open"}]))
json.dump(out, open(sys.argv[1], "w", encoding="utf-8", newline="\n"), indent=2)
print(len(out), "objects")
