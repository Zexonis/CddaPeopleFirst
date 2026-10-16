"""Generates mods/PeopleFirst/lab/lab_agents.json and lab_menu.json."""
import json, sys, os

K = range(5)
def m(expr): return {"math": [expr]}
def g(name): return {"global_val": name}
def msg(text, t="info"): return {"u_message": text, "type": t}
def eoc(id_, effect, comment=None, condition=None):
    o = {"type": "effect_on_condition", "id": id_}
    if comment: o["//"] = comment
    if condition: o["condition"] = condition
    o["effect"] = effect
    return o
def run_on(eocs, ids): return {"u_run_npc_eocs": eocs, "unique_ids": ids, "local": False}
LEAD = [g("pf_lab_lead_uid")]
MEMBERS = [g(f"pf_lab_m{k}") for k in K]
SPAWNED = m("value_or(pf_lab_spawned, 0) == 1")
NORTH = [m("pf_band_dx = 0"), m("pf_band_dy = -1"), {"run_eocs": "PF_BAND_heading"}]

agents = [
    {"type": "npc", "id": "PF_LAB_HUNTER",
     "//": "A-Life Lab test agent.  Mission 2 (shelter) turns off vanilla goal-seeking (the 'need_safety' trips to bandit camps), but the NPC still obeys u_set_guard_pos walk orders, still fights, and still flees.",
     "name_suffix": "hunter", "class": "NC_HUNTER", "attitude": 0, "mission": 2,
     "chat": "TALK_PF_LAB_HUNTER", "faction": "no_faction"},
    {"type": "talk_topic", "id": "TALK_PF_LAB_HUNTER",
     "dynamic_line": "We're on the trail of a deer.  Keep your voice down.\n\n[A-Life debug] id: <npc_val:pf_uid>  leader: <npc_val:pf_is_leader>  band: <npc_val:pf_band>  band size: <npc_val:pf_band_size>  member slot: <npc_val:pf_band_idx>  online: <npc_val:pf_online>  heading to waypoint: <npc_val:pf_goal_is_b>",
     "responses": [{"text": "Good hunting.", "topic": "TALK_DONE"}]},
    eoc("PF_LAB_spawn_person", [
        {"run_eocs": "PF_ALIFE_register_person"},
        {"u_spawn_npc": "PF_LAB_HUNTER", "unique_id": g("pf_person_uid"), "real_count": 1,
         "traits": ["PF_AGENT"], "min_radius": 2, "max_radius": 6},
        run_on(["PF_ALIFE_store_uid"], [g("pf_person_uid")]),
    ], "Spawns one hunter near the avatar with a fresh unique id (left in pf_person_uid)."),
    eoc("PF_LAB_spawn_band_here", [
        {"run_eocs": "PF_LAB_spawn_person"},
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_band_new_leader")},
        {"run_eocs": "PF_ALIFE_register_band"},
        run_on(["PF_LAB_init_leader"], [g("pf_band_new_leader")]),
        {"copy_var": g("pf_band_new_leader"), "target_var": g("pf_link_leader")},
        {"run_eocs": "PF_LAB_spawn_person"},
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_link_member")},
        {"run_eocs": "PF_BAND_link"},
        {"run_eocs": "PF_LAB_spawn_person"},
        {"copy_var": g("pf_person_uid"), "target_var": g("pf_link_member")},
        {"run_eocs": "PF_BAND_link"},
    ], "Spawns a band of three near the avatar: a leader and two members.  Leaves its index in pf_band_new_idx and its leader in pf_band_new_leader."),
    eoc("PF_LAB_init_leader", [m("u_pf_task = 1"), m("u_pf_online = 1"), m("u_pf_quarry_spawned = 1")]),
    eoc("PF_LAB_refresh", [
        {"set_string_var": "pf_slot_<global_val:pf_lab_band>", "target_var": {"context_val": "ref"}, "parse_tags": True},
        {"copy_var": {"var_val": "ref"}, "target_var": g("pf_lab_lead_uid")},
    ] + [{"set_string_var": "none", "target_var": g(f"pf_lab_m{k}")} for k in K] + [
        {"if": {"compare_string": [g("pf_lab_lead_uid"), "none"]},
         "then": [m("pf_lab_spawned = 0")],
         "else": [run_on(["PF_LAB_capture_members"], LEAD)]},
    ], "Looks up the lab band's current leader (it changes on succession) and members into pf_lab_lead_uid and pf_lab_m0..4.", condition=SPAWNED),
    eoc("PF_LAB_capture_members", [{"copy_var": {"u_val": f"pf_member_{k}"}, "target_var": g(f"pf_lab_m{k}")} for k in K]),
    eoc("PF_LAB_send_away_leader", [
        {"copy_var": g("pf_lab_wp_a"), "target_var": {"u_val": "pf_wp_a"}},
        {"copy_var": g("pf_lab_wp_b"), "target_var": {"u_val": "pf_wp_b"}},
        {"copy_var": g("pf_lab_wp_a"), "target_var": {"u_val": "pf_goal"}},
        m("u_pf_goal_is_b = 0"), m("u_pf_online = 0"), m("u_pf_quarry_spawned = 0"), m("pf_quarry_last_t = 0"),
        {"u_teleport": g("pf_lab_wp_a"), "force_safe": True},
        {"u_location_variable": {"u_val": "pf_vpos"}},
        {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_body"}},
        {"u_location_variable": g("pf_band_anchor")},
    ] + NORTH + [{"run_eocs": "PF_BAND_members_snap"}],
        "T1: teleport the leader far outside the bubble and set its patrol, then snap the members into formation there."),
    eoc("PF_LAB_recall_leader", [
        {"u_teleport": g("pf_player_pos"), "force_safe": True},
        {"u_location_variable": {"u_val": "pf_vpos"}},
        {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_body"}},
        {"u_location_variable": g("pf_band_anchor")},
    ] + NORTH + [{"run_eocs": "PF_BAND_members_snap"}]),
    eoc("PF_LAB_verify_near", [
        {"u_location_variable": {"u_val": "pf_after"}},
        {"if": m("distance(u_pf_after, pf_lab_check_at) <= pf_lab_check_r"),
         "then": [m("pf_lab_ok += 1")], "else": [m("pf_lab_fail += 1")]},
    ], "Counts this NPC as arrived if it is within pf_lab_check_r of pf_lab_check_at."),
    eoc("PF_LAB_locate_leader", [
        {"u_location_variable": g("pf_lab_lead_pos")},
        {"if": {"and": [m("has_var(u_pf_vpos)"), m("value_or(u_pf_online, 0) != 1")]},
         "then": [{"copy_var": {"u_val": "pf_vpos"}, "target_var": g("pf_lab_lead_pos")}]},
        m("pf_lab_lead_found = 1"),
        m("pf_lab_lead_dist = distance(pf_player_pos, pf_lab_lead_pos)"),
        m("pf_lab_lead_east = round((pf_lab_lead_pos.x - pf_player_pos.x) / 24)"),
        m("pf_lab_lead_south = round((pf_lab_lead_pos.y - pf_player_pos.y) / 24)"),
        m("pf_lab_lead_online = value_or(u_pf_online, 0)"),
    ]),
    eoc("PF_LAB_locate_member", [
        {"u_location_variable": {"u_val": "pf_pos"}},
        m("pf_lab_members_found += 1"),
        m("pf_lab_spread = max(pf_lab_spread, distance(u_pf_pos, pf_lab_lead_pos))"),
    ], "Run after PF_LAB_locate_leader.  Records each member's distance to the leader (spread)."),
    eoc("PF_LAB_remove_agent", [{"u_die": {"remove_corpse": True, "supress_message": True}}]),
    eoc("PF_LAB_kill_band", [run_on(["PF_LAB_remove_agent"], [{"u_val": f"pf_member_{k}"} for k in K]),
                             {"u_die": {"remove_corpse": True, "supress_message": True}}],
        "u = leader.  Members first, then the leader, so the death hook dissolves the band instead of passing it on."),
    eoc("PF_LAB_walk_test_leader", [
        {"copy_var": g("pf_lab_walk_target"), "target_var": {"u_val": "pf_walk_to"}},
        {"u_set_guard_pos": {"u_val": "pf_walk_to"}},
        {"copy_var": g("pf_lab_walk_target"), "target_var": g("pf_band_anchor")},
    ] + NORTH + [{"run_eocs": "PF_BAND_members_walk"}]),
    eoc("PF_LAB_perf_place", [
        {"u_location_variable": g("pf_player_pos")},
        {"copy_var": g("pf_player_pos"), "target_var": {"u_val": "pf_wp_a"}},
        {"location_variable_adjust": {"u_val": "pf_wp_a"}, "overmap_tile": True,
         "x_adjust": m("(rand(1) * 2 - 1) * (5 + rand(10))"), "y_adjust": m("rand(30) - 15")},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_wp_b"}},
        {"location_variable_adjust": {"u_val": "pf_wp_b"}, "overmap_tile": True,
         "x_adjust": m("rand(16) - 8"), "y_adjust": m("rand(16) - 8")},
        {"copy_var": {"u_val": "pf_wp_b"}, "target_var": {"u_val": "pf_goal"}},
        m("u_pf_goal_is_b = 1"), m("u_pf_online = 0"), m("u_pf_quarry_spawned = 0"), m("pf_quarry_last_t = 0"),
        {"u_teleport": g("pf_lab_perf_park"), "force_safe": True},
        {"u_location_variable": g("pf_band_anchor")},
    ] + NORTH + [{"run_eocs": "PF_BAND_members_snap"},
                 {"copy_var": g("pf_lab_perf_park"), "target_var": {"u_val": "pf_body"}},
                 {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_vpos"}}],
        "u = a perf band's leader.  Parks the bodies at the batch's shared spot (one map load for the whole batch instead of one per NPC), and starts the band's virtual position 5-15 overmap tiles east or west of the avatar, with a random patrol."),
    {"type": "npc", "id": "PF_LAB_CHILD",
     "//": "Kid NPC prototype.  Tiny (SMALL2) and PF_CHILD (CANNOT_ATTACK).  Mission 2 like the hunters.",
     "name_suffix": "child", "class": "NC_NONE", "attitude": 0, "mission": 2, "faction": "no_faction", "chat": "TALK_PF_LAB_CHILD"},
    {"type": "talk_topic", "id": "TALK_PF_LAB_CHILD",
     "dynamic_line": {"math": ["value_or(n_pf_orphaned, 0) == 1"],
                      "yes": "*hugs their knees and won't look up*  Everyone's gone.  I stayed where they told me.  I stayed right here.  [A-Life debug] id: <npc_val:pf_uid>  (orphaned)",
                      "no": "Are you a friend of my mom's?  [A-Life debug] id: <npc_val:pf_uid>  band: <npc_val:pf_band>  member slot: <npc_val:pf_band_idx>"},
     "responses": [{"text": "Stay close to your family.", "topic": "TALK_DONE", "condition": {"math": ["value_or(n_pf_orphaned, 0) != 1"]}},
                   {"text": "You did good.  You can stay with me.", "topic": "TALK_DONE", "condition": {"math": ["value_or(n_pf_orphaned, 0) == 1"]}}]},
    eoc("PF_LAB_spawn_child", [
        {"run_eocs": "PF_ALIFE_register_person"},
        {"u_spawn_npc": "PF_LAB_CHILD", "unique_id": g("pf_person_uid"), "real_count": 1,
         "traits": ["PF_AGENT", "SMALL2", "PF_CHILD"], "min_radius": 2, "max_radius": 6},
        run_on(["PF_ALIFE_store_uid"], [g("pf_person_uid")]),
    ]),
    eoc("PF_LAB_family_patrol", [
        {"u_location_variable": {"u_val": "pf_wp_a"}},
        {"location_variable_adjust": {"u_val": "pf_wp_a"}, "x_adjust": 2, "overmap_tile": True},
        {"u_location_variable": {"u_val": "pf_wp_b"}},
        {"location_variable_adjust": {"u_val": "pf_wp_b"}, "x_adjust": -2, "overmap_tile": True},
        {"copy_var": {"u_val": "pf_wp_a"}, "target_var": {"u_val": "pf_goal"}},
        m("u_pf_goal_is_b = 0"), m("u_pf_task = 0"), m("u_pf_online = 1"), m("u_pf_quarry_spawned = 1"),
        {"u_location_variable": {"u_val": "pf_vpos"}},
        {"copy_var": {"u_val": "pf_vpos"}, "target_var": {"u_val": "pf_body"}},
    ], "u = the family's parent.  Patrols 2 overmap tiles east and west of where it stands, on-screen, so you can watch the child follow."),
]

L = "[A-Life Lab] "
entries = []
def entry(key, name, desc, e): entries.append((key, name, desc, e))

run_all = eoc("PF_LAB_run_all", [
    {"if": {"not": SPAWNED}, "then": [{"run_eocs": "PF_LAB_spawn_band"}]},
    {"run_eocs": "PF_LAB_send_away"},
    {"run_eocs": "PF_LAB_locate"},
    m("pf_lab_found_before = pf_lab_lead_found + pf_lab_members_found"),
    {"copy_var": g("pf_lab_lead_pos"), "target_var": g("pf_lab_lead_pos_before")},
    {"run_eocs": "PF_ALIFE_run_tick", "iterations": 3},
    {"run_eocs": "PF_LAB_locate"},
    m("pf_lab_t2_moved = distance(pf_lab_lead_pos_before, pf_lab_lead_pos)"),
    msg(L + "===== SUMMARY ====="),
    {"if": m("pf_lab_t1_ok == 3"), "then": [msg("PASS  T1: the whole band teleported far outside the reality bubble.", "good")],
     "else": [msg("FAIL  T1: only <global_val:pf_lab_t1_ok> of 3 hunters arrived far away.", "bad")]},
    {"if": m("pf_lab_found_before == 3"), "then": [msg("PASS  REACH: scripts can find all three hunters while they are off-screen.", "good")],
     "else": [msg("FAIL  REACH: only <global_val:pf_lab_found_before> of 3 hunters reachable off-screen.", "bad")]},
    {"if": m("pf_lab_t2_moved >= 100"), "then": [msg("PASS  T2: the leader moved <global_val:pf_lab_t2_moved> tiles off-screen in 3 ticks.", "good")],
     "else": [msg("FAIL  T2: the leader moved only <global_val:pf_lab_t2_moved> tiles off-screen in 3 ticks (expected about 180).", "bad")]},
    {"run_eocs": "PF_LAB_watch"},
    {"run_eocs": "PF_ALIFE_run_tick"},
    m("pf_lab_handoff_quarry = pf_dbg_quarry"),
    {"run_eocs": "PF_LAB_locate"},
    {"if": {"and": [m("pf_lab_lead_online == 1"), m("pf_lab_lead_dist <= 40"), m("pf_lab_members_found == 2"), m("pf_lab_spread <= 5"), m("pf_lab_handoff_quarry == 1")]},
     "then": [msg("PASS  HANDOFF: the parked band was placed at its virtual position near you, in formation (farthest member <global_val:pf_lab_spread> tiles), with one deer.", "good")],
     "else": [msg("FAIL  HANDOFF: online <global_val:pf_lab_lead_online>, leader <global_val:pf_lab_lead_dist> tiles away, members <global_val:pf_lab_members_found> of 2, spread <global_val:pf_lab_spread>, quarry <global_val:pf_lab_handoff_quarry>.", "bad")]},
    msg(L + "Next: 'K' tests succession, 'P' adds 10 bands for performance, '6' then '5' shows the handoff."),
])

spawn = eoc("PF_LAB_spawn_band", [
    {"run_eocs": "PF_LAB_spawn_band_here"},
    m("pf_lab_band = pf_band_new_idx"),
    m("pf_lab_spawned = 1"),
    msg(L + "A band of three hunters (band <global_val:pf_lab_band>) spawned nearby.  Talk to them to see their debug state.", "good"),
], condition={"not": SPAWNED})

send = eoc("PF_LAB_send_away", [
    {"run_eocs": "PF_LAB_refresh"},
    {"u_location_variable": g("pf_lab_wp_a")},
    {"location_variable_adjust": g("pf_lab_wp_a"), "y_adjust": -8, "overmap_tile": True},
    {"u_location_variable": g("pf_lab_wp_b")},
    {"location_variable_adjust": g("pf_lab_wp_b"), "x_adjust": 8, "y_adjust": -16, "overmap_tile": True},
    run_on(["PF_LAB_send_away_leader"], LEAD),
    {"copy_var": g("pf_lab_wp_a"), "target_var": g("pf_lab_check_at")},
    m("pf_lab_check_r = 8"), m("pf_lab_ok = 0"), m("pf_lab_fail = 0"),
    run_on(["PF_LAB_verify_near"], LEAD + MEMBERS),
    m("pf_lab_t1_ok = pf_lab_ok"),
    msg(L + "T1 (bubble to far away): <global_val:pf_lab_ok> arrived, <global_val:pf_lab_fail> did not.  Now try 'Locate band'."),
], condition=SPAWNED)

locate = eoc("PF_LAB_locate", [
    {"run_eocs": "PF_LAB_refresh"},
    {"u_location_variable": g("pf_player_pos")},
    m("pf_lab_lead_found = 0"), m("pf_lab_members_found = 0"), m("pf_lab_spread = 0"),
    run_on(["PF_LAB_locate_leader"], LEAD),
    {"if": m("pf_lab_lead_found == 1"),
     "then": [run_on(["PF_LAB_locate_member"], MEMBERS),
              msg(L + "Band <global_val:pf_lab_band>, leader <global_val:pf_lab_lead_uid>: <global_val:pf_lab_lead_dist> tiles away (<global_val:pf_lab_lead_east> overmap tiles east, <global_val:pf_lab_lead_south> south).  Online: <global_val:pf_lab_lead_online>.  Members found: <global_val:pf_lab_members_found>, farthest <global_val:pf_lab_spread> tiles from the leader (off-screen, bodies stay parked while the band's position is virtual).")],
     "else": [msg(L + "Band leader: NOT FOUND.", "bad")]},
], condition=SPAWNED)

toggle_sim = eoc("PF_LAB_toggle_sim", [m("pf_alife_on = ( pf_alife_on == 1 ) ? 0 : 1"), msg(L + "Simulation is now <global_val:pf_alife_on> (1 = on).")])
tick_now = eoc("PF_LAB_tick_now", [m("_old_debug = pf_debug"), m("pf_debug = 1"), {"run_eocs": "PF_ALIFE_run_tick"}, m("pf_debug = _old_debug")])
watch = eoc("PF_LAB_watch", [
    {"copy_var": g("pf_lab_lead_pos"), "target_var": g("pf_lab_watch_at")},
    {"location_variable_adjust": g("pf_lab_watch_at"), "y_adjust": 30},
    {"u_teleport": g("pf_lab_watch_at"), "force_safe": True},
    {"copy_var": g("pf_lab_watch_at"), "target_var": g("pf_place_at")},
    {"run_eocs": "PF_ALIFE_avoid_water"},
    msg(L + "You arrive 30 tiles south of where the band leader was.  Run one tick to hand the band off."),
], condition=m("value_or(pf_lab_lead_found, 0) == 1"))
recall = eoc("PF_LAB_recall", [
    {"run_eocs": "PF_LAB_refresh"},
    {"u_location_variable": g("pf_player_pos")},
    run_on(["PF_LAB_recall_leader"], LEAD),
    {"copy_var": g("pf_player_pos"), "target_var": g("pf_lab_check_at")},
    m("pf_lab_check_r = 10"), m("pf_lab_ok = 0"), m("pf_lab_fail = 0"),
    run_on(["PF_LAB_verify_near"], LEAD + MEMBERS),
    msg(L + "T3 (far away to bubble): <global_val:pf_lab_ok> arrived, <global_val:pf_lab_fail> did not."),
], condition=SPAWNED)
toggle_debug = eoc("PF_LAB_toggle_debug", [m("pf_debug = ( pf_debug == 1 ) ? 0 : 1"), msg(L + "Debug log is now <global_val:pf_debug> (1 = on).")])
remove = eoc("PF_LAB_remove_band", [
    {"run_eocs": "PF_LAB_refresh"},
    run_on(["PF_LAB_kill_band"], LEAD),
    m("pf_lab_spawned = 0"), m("pf_lab_lead_found = 0"),
    msg(L + "Test band removed."),
], condition=SPAWNED)
walk = eoc("PF_LAB_walk_test", [
    {"run_eocs": "PF_LAB_refresh"},
    {"u_location_variable": g("pf_lab_walk_target"), "x_adjust": 10},
    run_on(["PF_LAB_walk_test_leader"], LEAD),
    msg(L + "Walk order given: the band should walk to a spot 10 tiles east of where you stand."),
], condition=SPAWNED)

kill_leader = eoc("PF_LAB_kill_leader", [
    {"run_eocs": "PF_LAB_locate"},
    m("pf_lab_members_before = pf_lab_members_found"),
    {"copy_var": g("pf_lab_lead_uid"), "target_var": g("pf_lab_old_lead")},
    run_on(["PF_LAB_remove_agent"], LEAD),
    {"run_eocs": "PF_LAB_refresh"},
    {"if": {"compare_string": [g("pf_lab_lead_uid"), "none"]},
     "then": [{"if": m("pf_lab_members_before == 0"),
               "then": [msg("PASS  SUCCESSION: the last hunter died and the band dissolved (its roster slot now reads 'none').", "good")],
               "else": [msg("FAIL  SUCCESSION: the band dissolved although <global_val:pf_lab_members_before> members were alive.", "bad")]}],
     "else": [{"run_eocs": "PF_LAB_locate"},
              {"if": {"and": [{"not": {"compare_string": [g("pf_lab_lead_uid"), g("pf_lab_old_lead")]}},
                              m("pf_lab_lead_found == 1"),
                              m("pf_lab_members_found == pf_lab_members_before - 1")]},
               "then": [msg("PASS  SUCCESSION: <global_val:pf_lab_old_lead> died; <global_val:pf_lab_lead_uid> now leads band <global_val:pf_lab_band> with <global_val:pf_lab_members_found> member(s).", "good")],
               "else": [msg("FAIL  SUCCESSION: leader <global_val:pf_lab_lead_uid> (was <global_val:pf_lab_old_lead>), found <global_val:pf_lab_lead_found>, members <global_val:pf_lab_members_found> (expected <global_val:pf_lab_members_before> minus 1).", "bad")]},
              msg(L + "Run a tick ('5') to check that the band still moves as one.")]},
], "Kills the lab band's leader and checks that a member took over (or that the band dissolved if nobody was left).", condition=SPAWNED)

kill_member = eoc("PF_LAB_kill_member", [
    {"run_eocs": "PF_LAB_locate"},
    m("pf_lab_members_before = pf_lab_members_found"),
    {"if": {"not": {"compare_string": [g("pf_lab_m0"), "none"]}}, "then": [run_on(["PF_LAB_remove_agent"], [g("pf_lab_m0")])],
     "else": [{"if": {"not": {"compare_string": [g("pf_lab_m1"), "none"]}}, "then": [run_on(["PF_LAB_remove_agent"], [g("pf_lab_m1")])],
               "else": [run_on(["PF_LAB_remove_agent"], [g("pf_lab_m2"), g("pf_lab_m3"), g("pf_lab_m4")])]}]},
    {"run_eocs": "PF_LAB_locate"},
    {"if": m("pf_lab_members_found == pf_lab_members_before - 1"),
     "then": [msg("PASS  MEMBER DEATH: the band dropped the dead member; <global_val:pf_lab_members_found> left.", "good")],
     "else": [msg("FAIL  MEMBER DEATH: members before <global_val:pf_lab_members_before>, after <global_val:pf_lab_members_found>.", "bad")]},
], condition=SPAWNED)

perf_one = eoc("PF_LAB_perf_one", [
    {"run_eocs": "PF_LAB_spawn_band_here"},
    run_on(["PF_LAB_perf_place"], [g("pf_band_new_leader")]),
    m("pf_lab_perf_n = value_or(pf_lab_perf_n, 0) + 1"),
])
perf = eoc("PF_LAB_perf_add", [
    {"u_location_variable": g("pf_lab_perf_park")},
    {"location_variable_adjust": g("pf_lab_perf_park"), "overmap_tile": True, "x_adjust": 20, "y_adjust": m("pf_lab_perf_n / 10 * 2")},
    {"run_eocs": "PF_LAB_perf_one", "iterations": 10},
    msg(L + "Added 10 bands of three, 5-15 overmap tiles away.  Perf bands: <global_val:pf_lab_perf_n>.  Roster slots: <global_val:pf_band_n>.  Turn the simulation on and time a 30-minute wait."),
])
bench = eoc("PF_LAB_bench", [
    m("_old_debug = pf_debug"), m("pf_debug = 0"),
    {"run_eocs": "PF_ALIFE_run_tick", "iterations": 30},
    m("pf_debug = _old_debug"),
    msg(L + "Benchmark: ran 30 A-Life ticks over <global_val:pf_dbg_agents> bands (no game time passed)."),
], "Runs 30 ticks inside one EOC: no game time passes, so no autosave, no 'Stop waiting?' prompts.  Time it from outside (CPU of the game process).")
bench_loop = eoc("PF_LAB_bench_loop_slot", [
    {"set_string_var": "pf_slot_<global_val:pf_band_i>", "target_var": {"context_val": "ref"}, "parse_tags": True},
    {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}}, "then": [m("pf_lab_bench_hits += 1")]},
    m("pf_band_i += 1"),
])
bench_reach = eoc("PF_LAB_bench_reach_slot", [
    {"set_string_var": "pf_slot_<global_val:pf_band_i>", "target_var": {"context_val": "ref"}, "parse_tags": True},
    {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}},
     "then": [run_on(["PF_LAB_bench_noop"], [{"var_val": "ref"}])]},
    m("pf_band_i += 1"),
])
bench_noop = eoc("PF_LAB_bench_noop", [m("pf_lab_bench_hits += 1")])
bench_tick_loop = eoc("PF_LAB_bench_tick_loop", [m("pf_band_i = 0"), {"run_eocs": "PF_LAB_bench_loop_slot", "condition": m("pf_band_i < pf_band_n"), "iterations": 100000}])
bench_tick_reach = eoc("PF_LAB_bench_tick_reach", [m("pf_band_i = 0"), {"run_eocs": "PF_LAB_bench_reach_slot", "condition": m("pf_band_i < pf_band_n"), "iterations": 100000}])
bench1 = eoc("PF_LAB_bench1", [m("pf_lab_bench_hits = 0"), {"run_eocs": "PF_LAB_bench_tick_loop", "iterations": 30},
    msg(L + "B1 (roster loop only): <global_val:pf_lab_bench_hits> live slots visited.")])
bench2 = eoc("PF_LAB_bench2", [m("pf_lab_bench_hits = 0"), {"run_eocs": "PF_LAB_bench_tick_reach", "iterations": 30},
    msg(L + "B2 (loop + reach each leader, empty EOC): <global_val:pf_lab_bench_hits> leaders reached.")])
family = eoc("PF_LAB_spawn_family", [
    {"run_eocs": "PF_LAB_spawn_person"},
    {"copy_var": g("pf_person_uid"), "target_var": g("pf_band_new_leader")},
    {"run_eocs": "PF_ALIFE_register_band"},
    {"copy_var": g("pf_band_new_leader"), "target_var": g("pf_link_leader")},
    {"run_eocs": "PF_LAB_spawn_child"},
    {"copy_var": g("pf_person_uid"), "target_var": g("pf_link_member")},
    {"run_eocs": "PF_BAND_link"},
    {"run_eocs": "PF_LAB_spawn_person"},
    {"copy_var": g("pf_person_uid"), "target_var": g("pf_link_member")},
    {"run_eocs": "PF_BAND_link"},
    run_on(["PF_LAB_family_patrol"], [g("pf_band_new_leader")]),
    m("pf_lab_band = pf_band_new_idx"), m("pf_lab_spawned = 1"),
    msg(L + "A family spawned nearby (band <global_val:pf_band_new_idx>): a parent, a child (slot 1) and another adult (slot 2).  It is now the lab's test band, so 'K' tests child-aware succession: the adult must inherit, not the child."),
])
kill_slot = eoc("PF_LAB_kill_slot", [
    {"set_string_var": "pf_slot_<global_val:pf_lab_x_i>", "target_var": {"context_val": "ref"}, "parse_tags": True},
    {"if": {"not": {"compare_string": [{"var_val": "ref"}, "none"]}},
     "then": [run_on(["PF_LAB_kill_band"], [{"var_val": "ref"}])]},
    m("pf_lab_x_i += 1"),
])
remove_all = eoc("PF_LAB_remove_all", [
    m("pf_lab_x_i = 0"),
    {"run_eocs": "PF_LAB_kill_slot", "condition": m("pf_lab_x_i < pf_band_n"), "iterations": 100000},
    m("pf_lab_spawned = 0"), m("pf_lab_lead_found = 0"), m("pf_lab_perf_n = 0"),
    msg(L + "Removed every band.  Deaths so far: <global_val:pf_deaths_total>, bands dissolved: <global_val:pf_dissolved_total>."),
])

items = [
    ("0", "0. RUN ALL CORE TESTS", "Spawns the band if needed, sends it far away (T1), locates it off-screen, runs 3 A-Life ticks, locates it again (T2), then teleports you 30 tiles from it and runs one more tick to check the handoff (HANDOFF).  Prints a PASS/FAIL summary.", run_all),
    ("1", "1. Spawn test band", "Spawns a band of three hunters next to you: a leader and two members.", spawn),
    ("2", "2. Send band far away (test T1)", "Teleports the band 8 overmap tiles north, far outside the reality bubble, in formation.  Patrol: waypoint A (8 north), then waypoint B (8 east, 16 north).", send),
    ("3", "3. Locate band", "Asks the world where the band is right now, even far outside the reality bubble, and how far each member is from the leader.", locate),
    ("4", "4. Toggle simulation", "Starts or pauses the A-Life tick (every game minute).  Off-screen, bands travel by abstract steps.  On-screen, they walk using the game's own pathfinding.", toggle_sim),
    ("5", "5. Run one A-Life tick now", "Runs a single A-Life tick immediately, without waiting a game minute.", tick_now),
    ("6", "6. Watch the band from 30 tiles away", "Teleports you 30 tiles south of the band leader's last located position.  The next tick hands the band off.  Run 'Locate band' first.", watch),
    ("7", "7. Recall band to me (test T3)", "Teleports the band from wherever it is to you, and checks that everyone arrived.", recall),
    ("8", "8. Toggle debug log", "Shows or hides the per-tick A-Life log message.", toggle_debug),
    ("9", "9. Remove test band", "Kills the test band (members first, then the leader; no corpses).  The death hook dissolves it.", remove),
    ("w", "W. Walk test (turn the simulation off first)", "Orders the band (if it is near you) to walk to a spot 10 tiles east of you, in formation.", walk),
    ("k", "K. Kill the band leader (succession test)", "Kills the test band's leader wherever it is.  A member should take over the band, its patrol and the other members.", kill_leader),
    ("j", "J. Kill one band member", "Kills one member of the test band.  The leader should drop it from the band.", kill_member),
    ("p", "P. Add 10 bands far away (performance)", "Spawns 10 bands of three and scatters them 5-15 overmap tiles away with random patrols.  Press repeatedly for 20, 50 or 100 bands.", perf),
    ("c", "C. Spawn a family (parent, child, adult)", "Spawns a parent, a child and another adult as one band, patrolling near you on-screen.  Tests the kid NPC (small body, never fights, follows the band) and child-aware succession.", family),
    ("b", "B. Benchmark: 30 ticks now", "Runs 30 A-Life ticks back to back without passing game time.  Time it from outside the game.", bench),
    ("y", "Y. Benchmark: roster loop only (30x)", "Profiling: visits every roster slot 30 times without touching any NPC.", bench1),
    ("z", "Z. Benchmark: loop + reach leaders (30x)", "Profiling: reaches every band leader by unique id 30 times with an empty EOC.", bench2),
    ("x", "X. Remove ALL bands", "Kills every band in the roster, including the test band.", remove_all),
]

menu = [eoc("PF_open_lab_menu", [{
    "run_eoc_selector": [i[3]["id"] for i in items],
    "names": [i[1] for i in items],
    "descriptions": [i[2] for i in items],
    "keys": [i[0] for i in items],
    "title": "A-Life Lab  |  sim on: <global_val:pf_alife_on>  debug log: <global_val:pf_debug>  roster slots: <global_val:pf_band_n>",
    "allow_cancel": True,
    "hilight_disabled": True}])] + [i[3] for i in items] + [kill_slot, perf_one, bench_loop, bench_reach, bench_noop, bench_tick_loop, bench_tick_reach]

outdir = sys.argv[1]
json.dump(agents, open(os.path.join(outdir, "lab_agents.json"), "w", encoding="utf-8", newline="\n"), indent=2)
json.dump(menu, open(os.path.join(outdir, "lab_menu.json"), "w", encoding="utf-8", newline="\n"), indent=2)
print(len(agents), len(menu))
