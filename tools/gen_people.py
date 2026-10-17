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
    # 2026-10-17: how close each grown-up who doesn't live with you is to a yes (PF_PM_bond_read), right on the list
    m("pf_bd_ok = 0"), {"run_eocs": "PF_PM_bond_read"},
    {"if": m("pf_bd_ok == 1"), "then": [{"set_string_var": "<global_val:pf_pm_tmp_role>, <global_val:pf_bd_bar>", "target_var": g("pf_pm_tmp_role"), "parse_tags": True}]},
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
    "run_eoc_selector": ["PF_PM_act_talk", "PF_PM_act_tend", "PF_PM_act_meal", "PF_PM_act_call", "PF_PM_act_fire", "PF_PM_act_supply", "PF_PM_act_flirt", "PF_PM_act_confess", "PF_PM_act_marry", "PF_PM_act_end", "PF_PM_act_takein", "PF_PM_act_stepadopt", "PF_PM_act_pickup", "PF_PM_act_setdown", "PF_PM_act_hand", "PF_PM_act_letgo", "PF_PM_act_teach", "PF_PM_act_invite", "PF_PM_act_where", "PF_PM_act_travel", "PF_PM_act_part", "PF_PM_act_movein", "PF_PM_act_role", "PF_PM_act_info", "PF_PM_moments_shown"],
    "names": ["Talk", "Tend their wounds", "Share a meal with them", "Call them over", "Ask them to sit by the fire", "Bring their people supplies", "Flirt", "Tell them how you feel", "Ask them to marry you", "End it", "Take them in", "Raise them as your own", "Pick them up", "Set them down", "Take their hand", "Let go of their hand", "Teach them something", "Ask them to come live with you", "Ask where they're headed", "Ask to travel with them", "Part ways with them", "Ask to live with them", "Ask them to take a different job", "What do I know about them?", "Moments (lab)"],
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
        g("pf_pm_inv_desc"),
        "Where their people will be over the next couple of weeks.  It goes on your map, so you can find them again.",
        "Go where they go.  Their leader decides the road and where to sleep; they wait if you fall behind and share their supper.  They answer from their own view of you.",
        "Go your own way.  They'll tell you where to find them.",
        "Their home becomes yours: everyone who lives there, and their leader runs the place.  They answer as they would to living with you.  You can't leave people of your own behind.",
        "Cook, guard, forager, tinkerer, carer: the next one in line.",
        "How they seem to see you, how you see them, and what you've picked up about them.",
        "[lab] Make something happen between you and them, and watch the bond spine react."],
    "keys": ["t", "n", "a", "c", "f", "y", "r", "l", "p", "e", "h", "w", "u", "d", "o", "g", "s", "v", "k", "j", "q", "z", "b", "i", "m"],
    "title": "<global_val:pf_pm_sel_label><global_val:pf_pm_sel_bondtxt>",
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
    # 2026-10-17: the bond meter in the screen's title, and what would help in the invitation's description
    {"set_string_var": "", "target_var": g("pf_pm_sel_bondtxt")},
    {"set_string_var": "Home has room.  They'll answer from their own heart; if they travel with a band, the whole band comes.", "target_var": g("pf_pm_inv_desc")},
    # v0.9 (gen_places): their band's leader is settled or lives at a place (Ask to live with them); you travel with their band (Part ways)
    m("pf_pm_sel_lhome = 0"), m("pf_wh_ok = 0"), {"run_eocs": "PF_WHERE_get_lead", "alpha_talker": "npc"},
    {"if": m("pf_wh_ok == 1"), "then": [{"u_run_npc_eocs": [{"id": "PF_PM_lead_flags", "effect": [
        m("pf_pm_sel_lhome = (value_or(u_pf_settled, 0) == 1) + (value_or(u_pf_place, 0) > 0) > 0")]}],
        "unique_ids": [g("pf_wh_lead")], "local": False}]},
    m("pf_pm_sel_tvband = (value_or(pf_tv_on, 0) == 1) * (value_or(n_pf_band, 0) > 0) * (value_or(n_pf_band, 0) == value_or(pf_tv_band, -1))"),
    m("pf_bd_ok = 0"), {"run_eocs": "PF_PM_bond_read", "alpha_talker": "npc"},
    {"if": m("pf_bd_ok == 1"), "then": [
        {"set_string_var": "  <global_val:pf_bd_word>", "target_var": g("pf_pm_sel_bondtxt"), "parse_tags": True},  # the label has the bar
        {"set_string_var": "Home has room.  They'll answer from their own heart; if they travel with a band, the whole band comes.  Right now: <global_val:pf_bd_bar> <global_val:pf_bd_word>  <global_val:pf_bd_hint>",
         "target_var": g("pf_pm_inv_desc"), "parse_tags": True}]},


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
              msg("One <global_val:pf_ml_food>, split two ways."),
              # 2026-10-17: the meter, and (the first time with a band) where to find them again
              {"run_eocs": "PF_PM_bond_report"}, m("pf_wh_auto = 1"), {"run_eocs": "PF_WHERE_ask"}]},
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
    {"run_eocs": "PF_PM_bond_report"},
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
            m("pf_supplies_given_total = value_or(pf_supplies_given_total, 0) + 1"),
            {"run_eocs": "PF_PM_bond_report", "beta_talker": g("pf_pm_sel_id")},
            m("pf_wh_auto = 1"), {"run_eocs": "PF_WHERE_ask", "beta_talker": g("pf_pm_sel_id")}]}]},
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
# ---------------------------------------------------------------- getting to know people (2026-10-17, the user)
# "I couldn't see or feel that I was making progress with the strangers... I couldn't tell if it was making a difference.
# Worse, I felt like if I failed to connect in that moment, I might never see them again when they wander off."
# 1. A visible bond meter: how close someone is to saying yes to living with you, from their own view of you (the same
#    numbers PF_HOME_invite reads), with what would help.  Shown on the People nearby list, the person screen, after a
#    meal, supplies or tending, and with a "not yet".
# 2. "Ask where they're headed": a band says where it will be, makes camp there for a while, and you get a map mark
#    (a mission marker) for two weeks.  The first time you share a meal or bring supplies, they tell you on their own.
def by_uid(eocs, uid): return {"u_run_npc_eocs": eocs, "unique_ids": [uid], "local": False}
def compass(dx, dy, out):
    """Effects: a compass word (north, southeast...) for an offset, into global `out` (y grows southward).  As gen_hearts."""
    return [{"set_string_var": "", "target_var": g(out + "_ns")}, {"set_string_var": "", "target_var": g(out + "_ew")},
            {"if": m(f"abs({dy}) * 2 >= abs({dx})"), "then": [
                {"if": m(f"{dy} < 0"), "then": [{"set_string_var": "north", "target_var": g(out + "_ns")}],
                 "else": [{"set_string_var": "south", "target_var": g(out + "_ns")}]}]},
            {"if": m(f"abs({dx}) * 2 >= abs({dy})"), "then": [
                {"if": m(f"{dx} < 0"), "then": [{"set_string_var": "west", "target_var": g(out + "_ew")}],
                 "else": [{"set_string_var": "east", "target_var": g(out + "_ew")}]}]},
            {"set_string_var": f"<global_val:{out}_ns><global_val:{out}_ew>", "target_var": g(out), "parse_tags": True}]
def setg(var, text, parse=False):
    o = {"set_string_var": text, "target_var": g(var)}
    if parse: o["parse_tags"] = True
    return o

BOND_BARS = ["[-----]", "[#----]", "[##---]", "[###--]", "[####-]", "[#####]"]
BOND_WORDS = ["They don't know you yet.", "They've started to notice you.", "They're getting to know you.",
              "They like having you around.", "They're nearly ready to throw in with you.", "They'd say yes if you asked them to live with you."]
# u = an adult who doesn't live with you and isn't your sweetheart
BOND_OK = {"and": [{"not": {"u_has_trait": "PF_CHILD"}}, m("u_val('age') >= 18"), m("value_or(u_pf_resident, 0) == 0"),
                   {"not": {"and": [m("value_or(u_pf_has_sweet, 0) == 1"), {"compare_string": [{"u_val": "pf_sweet"}, "AVATAR"]}]}}]}
out.append(eoc("PF_PM_bond_read", [
    {"run_eocs": "PF_ID_ensure"},
    {"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
    m("pf_bd_ok = 1"), setg("pf_bd_name", "<u_name>", True),
    m("_w = max(pf_read_w, 0)"), m("_t = max(pf_read_t, 0)"),
    # the invitation's own test (gen_home PF_HOME_invite): warmth 35 and trust 25, or warmth 50 and trust 15
    m("pf_bd_ready = (_w >= 35) * (_t >= 25) + (_w >= 50) * (_t >= 15) > 0"),
    m("pf_bd_p = max(min(min(_w / 35, _t / 25), 1), min(min(_w / 50, _t / 15), 1))"),
    m("pf_bd_pips = pf_bd_ready == 1 ? 5 : min(4, floor(pf_bd_p * 5))"),
    m("pf_bd_up = pf_bd_pips > value_or(u_pf_bond_seen, 0)"), m("u_pf_bond_seen = pf_bd_pips"),
    {"switch": m("pf_bd_pips"), "cases": [{"case": i, "effect": [setg("pf_bd_bar", BOND_BARS[i]), setg("pf_bd_word", BOND_WORDS[i])]} for i in range(6)]},
    {"if": m("pf_bd_ready == 1"),
     "then": [{"if": m("value_or(pf_home_set, 0) == 1"), "then": [setg("pf_bd_hint", "Ask them to come live with you.")],
               "else": [setg("pf_bd_hint", "Make a place your home first (People First menu: Home), then ask them.")]}],
     "else": [{"if": m("pf_read_x >= 25"), "then": [setg("pf_bd_hint", "Something sits wrong between you.  Give it a few days.")],
               "else": [{"if": m("_t / 25 < _w / 35"),
                         "then": [setg("pf_bd_hint", "They like you, but they don't trust you yet: tend their wounds, bring their people supplies, stand with them in a fight.")],
                         "else": [setg("pf_bd_hint", "Time together is what they need: eat with them once a day, sit by the fire, talk.")]}]}]},
], "u = an adult who doesn't live with you.  Their own view of you, as a 5-step meter toward a yes to living with you (pf_bd_bar, pf_bd_word, pf_bd_hint; pf_bd_up = a step up since you last looked).",
    condition=BOND_OK))
out.append(eoc("PF_PM_bond_report", [
    m("pf_bd_ok = 0"), {"run_eocs": "PF_PM_bond_read", "alpha_talker": "npc"},
    {"if": m("pf_bd_ok == 1"), "then": [
        {"if": m("pf_bd_up == 1"),
         "then": [msg("Where you stand with <global_val:pf_bd_name>: <global_val:pf_bd_bar> <global_val:pf_bd_word>  A step closer than before.", "good")],
         "else": [msg("Where you stand with <global_val:pf_bd_name>: <global_val:pf_bd_bar> <global_val:pf_bd_word>")]}]},
], "u = you, npc = the person.  After a meal, supplies or tending: the meter, and whether it moved."))

# ---- where they'll be: map marks.  Missions with no giver and an MGOAL_CONDITION goal never complete on their own
# (mission.cpp is_complete), so a mark doesn't vanish when you walk onto it; it ends when PF_MARK_tick removes it.
MARKS = 6
for k in range(MARKS):
    out.append({"id": f"PF_MARK_{k}", "type": "mission_definition", "name": {"str": f"Where they said they'd be ({k + 1})"},
                "goal": "MGOAL_CONDITION", "difficulty": 0, "value": 0, "invisible_on_complete": True,
                "description": "Someone you met on the road told you where to find their people.  The People First menu (Where to find people) says who.  The mark is good for about two weeks.",
                "start": {"assign_mission_target": {"var": g("pf_mk_target")}}})
out.append(eoc("PF_PM_act_where", [m("pf_wh_auto = 0"), {"run_eocs": "PF_WHERE_ask", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_where", "effect": [msg("They're not here anymore.")]}]}],
    condition={"and": [m("pf_pm_sel_band == 1"), m("value_or(pf_pm_sel_res, 0) == 0"), m("value_or(pf_pm_sel_adult, 0) == 1")]}))
# v0.9 Their own lives (gen_places): travel with a band, part ways, live at their place
SEL_BAND_STRANGER = [m("pf_pm_sel_band == 1"), m("value_or(pf_pm_sel_res, 0) == 0"), m("value_or(pf_pm_sel_adult, 0) == 1")]
out.append(eoc("PF_PM_act_travel", [{"run_eocs": "PF_TRAVEL_ask", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_travel", "effect": [msg("They're not here anymore.")]}]}],
    condition={"and": SEL_BAND_STRANGER + [m("value_or(pf_tv_on, 0) == 0")]}))
out.append(eoc("PF_PM_act_part", [{"run_eocs": "PF_TRAVEL_part", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_part", "effect": [msg("They're not here anymore.")]}]}],
    condition=m("value_or(pf_pm_sel_tvband, 0) == 1")))
out.append(eoc("PF_PM_act_movein", [{"run_eocs": "PF_PLACE_move_in", "beta_talker": g("pf_pm_sel_id"),
    "false_eocs": [{"id": "PF_PM_gone_movein", "effect": [msg("They're not here anymore.")]}]}],
    condition={"and": SEL_BAND_STRANGER + [m("value_or(pf_pm_sel_lhome, 0) == 1")]}))
out.append(eoc("PF_WHERE_get_lead", [
    setg("pf_wh_who", "<u_name>", True),
    {"if": m("value_or(u_pf_is_leader, 0) == 1"), "then": [{"copy_var": {"u_val": "pf_uid"}, "target_var": g("pf_wh_lead")}, m("pf_wh_ok = 1")],
     "else": [{"if": m("has_var(u_pf_leader)"), "then": [{"copy_var": {"u_val": "pf_leader"}, "target_var": g("pf_wh_lead")}, m("pf_wh_ok = 1")]}]},
], "u = someone in a band (not living with you).  pf_wh_lead = their band's leader (the band's data lives there).",
    condition={"and": [m("value_or(u_pf_band, 0) > 0"), m("value_or(u_pf_resident, 0) == 0")]}))
out.append(eoc("PF_WHERE_leader", [
    setg("pf_wh_lname", "<u_name>", True),
    m("pf_wh_days = 14"),
    {"if": m("(pf_wh_auto == 1) * (value_or(u_pf_mark_until, 0) > time('now'))"), "then": [m("pf_wh_kind = -1")], "else": [
        {"if": m("(value_or(u_pf_visiting, 0) == 1) + (value_or(u_pf_joining, 0) == 1) > 0"), "then": [m("pf_wh_kind = 4")], "else": [
          # v0.9: people of a place say so (6 they live there, 7 hunters who hunt out of it), and the place becomes known to you
          {"if": m("(value_or(u_pf_place, 0) > 0) * ((value_or(u_pf_settled, 0) == 1) + (value_or(u_pf_based, 0) == 1) > 0)"),
           "then": [m("pf_wh_kind = value_or(u_pf_based, 0) == 1 ? 7 : 6"),
                    {"copy_var": {"u_val": "pf_place_at"}, "target_var": g("pf_wh_at")},
                    {"copy_var": {"u_val": "pf_place_name"}, "target_var": g("pf_wh_place")}] + [
                    {"if": m(f"u_pf_place == {k + 1}"), "then": [m(f"pf_pl_{k}_known = 1")]} for k in range(6)],
           "else": [
            {"if": m("value_or(u_pf_settled, 0) == 1"),
             "then": [m("pf_wh_kind = 1"), {"copy_var": {"u_val": "pf_home"}, "target_var": g("pf_wh_at")}],
             "else": [{"if": m("value_or(u_pf_camp_until, 0) > time('now')"),
                       "then": [m("pf_wh_kind = 2"), {"copy_var": {"u_val": "pf_camp"}, "target_var": g("pf_wh_at")},
                                m("pf_wh_days = floor((u_pf_camp_until - time('now') + time('1 d') - 1) / time('1 d'))")],
                       # on the move: they make camp, either right here (if they like you, or half the time) or where they were going
                       "else": [{"set_string_var": "AVATAR", "target_var": g("pf_m_other")}, {"run_eocs": "PF_VIEW_read"},
                                {"if": m("(pf_read_w >= 10) + (rand(1) == 0) > 0"),
                                 "then": [m("pf_wh_kind = 3"), {"copy_var": {"u_val": "pf_vpos"}, "target_var": g("pf_wh_at")}],
                                 "else": [m("pf_wh_kind = 5"), {"copy_var": {"u_val": "pf_vpos"}, "target_var": g("pf_wh_at")},
                                          {"if": m("has_var(u_pf_goal)"), "then": [{"copy_var": {"u_val": "pf_goal"}, "target_var": g("pf_wh_at")}]}]},
                                {"run_eocs": "PF_WHERE_make_camp"}]}]}]}]}]},
    {"if": m("(pf_wh_kind > 0) * (pf_wh_kind != 4)"), "then": [m("u_pf_mark_until = time('now') + time('1 d') * pf_wh_days")]},
], "u = a band's leader (by unique id; off-screen is fine: only its variables are read).  pf_wh_kind: 1 their home (settled), 2 camped already, 3 camping right here, 4 on their way to you, 5 camping where they were headed; -1 they already told you (an automatic telling)."))
out.append(eoc("PF_WHERE_make_camp", [
    {"copy_var": g("pf_wh_at"), "target_var": {"u_val": "pf_camp"}},
    {"copy_var": g("pf_wh_at"), "target_var": {"u_val": "pf_wp_a"}}, {"copy_var": g("pf_wh_at"), "target_var": {"u_val": "pf_wp_b"}},
    {"copy_var": g("pf_wh_at"), "target_var": {"u_val": "pf_goal"}}, m("u_pf_goal_is_b = 0"),
    m("u_pf_camp_until = time('now') + time('14 d')"),
    m("pf_camps_told_total = value_or(pf_camps_told_total, 0) + 1"),
], "u = a band's leader.  The band makes camp at pf_wh_at for two weeks: both its waypoints are the camp, so A-Life keeps it there, on-screen or off (gen_home PF_WORLD_drift_one leaves a camping band alone, then sends it back on the road)."))
# kind: (said when the spot is under 2 map tiles away, said otherwise)
WHERE_SAY = {
    1: ("<global_val:pf_wh_who> nods at the houses close by.  \"This is home now.  Come by any time.\"",
        "<global_val:pf_wh_who> points <global_val:pf_wh_dir>.  \"Home's that way, about <global_val:pf_wh_mt> map tiles.  Come by any time.\""),
    2: ("<global_val:pf_wh_who> waves at the ground around you.  \"We're camped right here, another <global_val:pf_wh_days> days or so.\"",
        "<global_val:pf_wh_who> points <global_val:pf_wh_dir>.  \"We're camped about <global_val:pf_wh_mt> map tiles that way, another <global_val:pf_wh_days> days or so.\""),
    3: ("<global_val:pf_wh_who> looks around.  \"We like it here.  We'll camp close by for a couple of weeks.\"",
        "<global_val:pf_wh_who> looks around.  \"We like it here.  We'll camp close by for a couple of weeks.\""),
    5: ("<global_val:pf_wh_who> nods at the ground ahead.  \"We're stopping just up here for a couple of weeks.\"",
        "<global_val:pf_wh_who> points <global_val:pf_wh_dir>.  \"We're making for a spot about <global_val:pf_wh_mt> map tiles that way.  We'll stop there a couple of weeks.\""),
    6: ("<global_val:pf_wh_who> spreads their arms.  \"This is <global_val:pf_wh_place>.  We live here.  Come by any time.\"",
        "<global_val:pf_wh_who> points <global_val:pf_wh_dir>.  \"We live at <global_val:pf_wh_place>, about <global_val:pf_wh_mt> map tiles that way.  Come by any time.\""),
    7: ("<global_val:pf_wh_who> nods at the houses.  \"We hunt out of here, <global_val:pf_wh_place>.\"",
        "<global_val:pf_wh_who> points <global_val:pf_wh_dir>.  \"We hunt out of <global_val:pf_wh_place>, about <global_val:pf_wh_mt> map tiles that way.\""),
}
def where_say(kind):
    near, far = WHERE_SAY[kind]
    return [{"if": m("pf_wh_mt < 2"), "then": [msg(near)], "else": [msg(far)]}]
out.append(eoc("PF_WHERE_ask", [
    m("pf_wh_ok = 0"), m("pf_wh_kind = 0"),
    {"run_eocs": "PF_WHERE_get_lead", "alpha_talker": "npc"},
    {"if": m("pf_wh_ok == 1"), "then": [by_uid(["PF_WHERE_leader"], g("pf_wh_lead"))]},
    {"if": m("pf_wh_auto == 0"), "then": [
        {"if": m("pf_wh_ok == 0"), "then": [msg("<npc_name> shrugs.  \"Wherever the road goes.\"")]},
        {"if": m("pf_wh_kind == 4"), "then": [msg("<npc_name> grins.  \"We're on our way to your place.\"")]}]},
    {"if": m("(pf_wh_kind > 0) * (pf_wh_kind != 4)"), "then": [
        {"u_location_variable": g("pf_wh_av")},
        m("pf_wh_dx = pf_wh_at.x - pf_wh_av.x"), m("pf_wh_dy = pf_wh_at.y - pf_wh_av.y"),
        m("pf_wh_mt = floor((max(abs(pf_wh_dx), abs(pf_wh_dy)) + 12) / 24)")] + compass("pf_wh_dx", "pf_wh_dy", "pf_wh_dir") + [
        {"if": m("pf_wh_auto == 1"), "then": [msg("Before you part, <global_val:pf_wh_who> tells you where to find them.")]}] + [
        {"if": m(f"pf_wh_kind == {kd}"), "then": where_say(kd)} for kd in (1, 2, 3, 5, 6, 7)] + [
        {"run_eocs": "PF_MARK_set"},
        msg("It's on your map: the Missions screen lists it as \"Where they said they'd be (<global_val:pf_mk_shown>)\", and the People First menu as Where to find people.", "good")]},
], "u = you, npc = someone in a band.  They say where their people will be (making camp if they're on the move) and you get a map mark.  pf_wh_auto = 1 when it comes up by itself after a meal or supplies: silent if they've told you already."))
set_slot = [m("pf_mk_slot = -1"), m("pf_mk_best = time('now') + time('999 d')")]
for k in range(MARKS):  # their old mark first, else the slot that runs out soonest (an empty one is 0)
    set_slot.append({"if": {"and": [m(f"value_or(pf_mk_{k}_until, 0) > 0"), {"compare_string": [g(f"pf_mk_{k}_lead"), g("pf_wh_lead")]}]},
                     "then": [m(f"pf_mk_slot = {k}"), m("pf_mk_best = -1")]})
for k in range(MARKS):
    set_slot.append({"if": m(f"value_or(pf_mk_{k}_until, 0) < pf_mk_best"), "then": [m(f"pf_mk_slot = {k}"), m(f"pf_mk_best = value_or(pf_mk_{k}_until, 0)")]})
for k in range(MARKS):
    set_slot.append({"if": m(f"pf_mk_slot == {k}"), "then": [
        {"remove_active_mission": f"PF_MARK_{k}"},
        {"copy_var": g("pf_wh_at"), "target_var": g("pf_mk_target")},
        {"assign_mission": f"PF_MARK_{k}", "deadline": m("time('now') + time('1 d') * (pf_wh_days + 1)")},
        {"copy_var": g("pf_wh_lead"), "target_var": g(f"pf_mk_{k}_lead")},
        {"copy_var": g("pf_wh_at"), "target_var": g(f"pf_mk_{k}_at")},
        setg(f"pf_mk_{k}_name", "<global_val:pf_wh_lname>'s people", True),
        m(f"pf_mk_{k}_until = time('now') + time('1 d') * pf_wh_days"),
        m(f"pf_mk_shown = {k + 1}")]})
out.append(eoc("PF_MARK_set", set_slot + [m("pf_marks_total = value_or(pf_marks_total, 0) + 1")],
    "u = you.  Puts the band pf_wh_lead's spot (pf_wh_at) on your map for pf_wh_days days: their old mark if they had one, else the mark that runs out soonest.  The mission's own deadline is a day later; PF_MARK_tick takes it off first (a deadline counts as a failed mission)."))
mark_tick = []
for k in range(MARKS):
    mark_tick += [
        {"if": m(f"(value_or(pf_mk_{k}_until, 0) > 0) * (value_or(pf_mk_{k}_until, 0) <= time('now'))"),
         "then": [{"remove_active_mission": f"PF_MARK_{k}"}, m(f"pf_mk_{k}_until = 0")]},
        # they moved in with you (or anywhere: no longer a band's leader): the mark goes.  A dead leader's id is never reached.
        {"if": m(f"value_or(pf_mk_{k}_until, 0) > time('now')"), "then": [
            {"set_string_var": f"pf_reg_<global_val:pf_mk_{k}_lead>_dead", "target_var": {"context_val": "md"}, "parse_tags": True},
            m("pf_mk_gone = 0"),
            {"if": m("value_or(v_md, 0) == 0"), "then": [by_uid([{"id": f"PF_MARK_check_{k}", "effect": [{"if": m("value_or(u_pf_is_leader, 0) != 1"), "then": [m("pf_mk_gone = 1")]}]}], g(f"pf_mk_{k}_lead"))]},
            {"if": m("pf_mk_gone == 1"), "then": [{"remove_active_mission": f"PF_MARK_{k}"}, m(f"pf_mk_{k}_until = 0")]}]}]
out.append(eoc("PF_MARK_tick", mark_tick, "Hourly: marks that ran out (or whose band moved in) come off your map.",
    recurrence="1 hours", **{"global": True}, condition=m(" + ".join(f"value_or(pf_mk_{k}_until, 0)" for k in range(MARKS)) + " > 0")))
mark_list = [m("pf_mk_n = 0"), {"u_location_variable": g("pf_wh_av")}]
for k in range(MARKS):
    mark_list.append({"if": m(f"value_or(pf_mk_{k}_until, 0) > time('now')"), "then": [
        m("pf_mk_n += 1"),
        m(f"pf_wh_dx = pf_mk_{k}_at.x - pf_wh_av.x"), m(f"pf_wh_dy = pf_mk_{k}_at.y - pf_wh_av.y"),
        m("pf_wh_mt = floor((max(abs(pf_wh_dx), abs(pf_wh_dy)) + 12) / 24)"),
        m(f"pf_wh_days = floor((pf_mk_{k}_until - time('now') + time('1 d') - 1) / time('1 d'))")] + compass("pf_wh_dx", "pf_wh_dy", "pf_wh_dir") + [
        {"if": m("pf_wh_mt < 2"),
         "then": [msg(f"<global_val:pf_mk_{k}_name>: close by, for another <global_val:pf_wh_days> days or so.  (Missions: Where they said they'd be ({k + 1}))")],
         "else": [msg(f"<global_val:pf_mk_{k}_name>: about <global_val:pf_wh_mt> map tiles <global_val:pf_wh_dir> of here, for another <global_val:pf_wh_days> days or so.  (Missions: Where they said they'd be ({k + 1}))")]}]})
mark_list.append({"run_eocs": "PF_PLACE_list_known"})  # v0.9: the places people made that you know of
mark_list.append({"if": m("pf_mk_n + value_or(pf_pl_shown, 0) == 0"), "then": [msg("Nobody has told you where to find them lately.  Ask someone in a band where they're headed (People nearby), or share a meal with them.")]})
mark_list.append({"if": m("pf_mk_n > 0"), "then": [msg("Pick one on the Missions screen to point your compass at it.")]})
out.append(eoc("PF_MARK_list", mark_list, "People First menu: Where to find people.  Every band that told you where it will be, with how far, which way, and for how long."))

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
