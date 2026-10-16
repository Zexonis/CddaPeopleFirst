"""People First engine patch set for Cataclysm-DDA 0.I "Ito" (commit 27939e29b8b4ddc081490d9f51de59a459c88df6).

Usage: python -I engine/apply_patches.py C:/pfbuild/cdda
Idempotent: each patch checks for its marker ("People First:") before applying.  Fails loudly if an anchor moved.

1. Crash safety: run_eocs with an alpha_talker/beta_talker that no longer exists (left the bubble, died) runs its
   false_eocs instead of running with a null actor (which segfaulted).  The "no valid talker" and
   "Tried to use invalid npc" popups become debug.log warnings: the mod expects these cases.
2. u_set_name / npc_set_name: set a character's name.  {"u_set_name": {"first": ..., "last": ..., "full": ...,
   "last_from_other": true}}.  Each part is a string or variable object; empty means keep.  last_from_other takes the
   other talker's surname (the last word of their name).  The mod uses it so children born to or adopted by a couple
   carry the family name and a first name the player chooses (string_input prompt in JSON).
3. The vanilla "let me pass" bark (an NPC shoving another NPC or the player out of the way) is said at most once every
   15 minutes per NPC.  In crowds with walk orders it fired every turn.
4. Characters with CANNOT_ATTACK (children, babies) don't go looking for corpses to pulp.
5. Walking into an NPC with the PF_SWAP character flag swaps places (like a follower) instead of opening the NPC menu,
   whose next keypress could be "attack".
6. NPCs stand up for the people they're bonded to (kin, partner, band, household, or warmth >= pf_defend_w, default 40),
   the player included: a monster near one of them gets top priority, and they don't shoot through them.  Vanilla only
   does this for faction mates, and the mod's people are lone wolves.  Global pf_set_defend = 0 turns it off.
7-10. See engine/README.md (follower rules, closing in, who ran, the People key).
11. The fork's title screen: data/title/people_first.title (engine/make_title.py) and "People First" under the version.
12. "<npcname> wields a ..." names the NPC (vanilla bug).
13. A shot that runs off the edge of the map ends quietly instead of raising an error screen (vanilla bug).
14. In the dark you hear what you can't see: our people count an unseen hostile monster within 3 tiles, or one right next
   to someone they protect (within 12 tiles), and keep a protected person within 10 tiles as a friend without seeing them.
   An unseen target more than a tile away is walked up to (a gun can't be aimed at what you can't see).
15. An item moved by an EOC teleport (the mod's housekeeping: tidying, a dead resident's things) loses its old owner, so
   the household's stores never read as stealing.
"""
import sys, pathlib

root = pathlib.Path(sys.argv[1]) / "src"

def patch(fname, anchor, replacement, marker):
    p = root / fname
    s = p.read_text(encoding="utf-8")
    if marker in s:
        print(f"  {fname}: already has '{marker}'")
        return
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"{fname}: anchor found {n} times: {anchor[:80]!r}")
    p.write_text(s.replace(anchor, replacement), encoding="utf-8", newline="\n")
    print(f"  {fname}: applied '{marker}'")

# ---------------------------------------------------------------- 1. crash safety
patch("npctalk.cpp",
      '''    debugmsg( R"(run_eocs error: no valid talker\\n%s)", d.get_callstack() );
    return {};
}''',
      '''    // People First: a talker that's gone (left the bubble, died) is an expected case, not a popup.
    DebugLog( D_WARNING, D_GAME ) << "run_eocs: no valid talker (gone?) " << d.get_callstack();
    return {};
}''', "a talker that's gone")

patch("npctalk.cpp",
      '''        std::unique_ptr<talker> alpha = get_talker( d, alpha_var, alpha_loc, false );
        std::unique_ptr<talker> beta = get_talker( d, beta_var, beta_loc, true );
        if( !alpha && !beta ) {
            run_eoc_vector( false_eocs, d );
            return;
        }''',
      '''        std::unique_ptr<talker> alpha = get_talker( d, alpha_var, alpha_loc, false );
        std::unique_ptr<talker> beta = get_talker( d, beta_var, beta_loc, true );
        // People First: if a talker was asked for by id or location and can't be found, don't run the EOCs
        // with a null actor (that segfaulted); treat it like "no talker" and run the false_eocs.
        const bool alpha_missing = !alpha && ( alpha_loc || ( alpha_var && !alpha_var->evaluate( d ).empty() ) );
        const bool beta_missing = !beta && ( beta_loc || ( beta_var && !beta_var->evaluate( d ).empty() ) );
        if( ( !alpha && !beta ) || alpha_missing || beta_missing ) {
            run_eoc_vector( false_eocs, d );
            return;
        }''', "if a talker was asked for by id or location")

patch("npctalk.cpp",
      '''                            debugmsg( "Tried to use invalid npc: %s. %s", target.evaluate( d ), d.get_callstack() );''',
      '''                            // People First: a unique id whose NPC is gone is expected; log it instead of a popup.
                            DebugLog( D_WARNING, D_GAME ) << "Tried to use invalid npc: " << target.evaluate( d ) << ". " << d.get_callstack();''',
      "a unique id whose NPC is gone")

# ---------------------------------------------------------------- 2. set_name
patch("npctalk.cpp",
      '''talk_effect_fun_t::func f_lose_morale( const JsonObject &jo, std::string_view member,
                                       std::string_view, bool is_npc )
{''',
      '''// People First: u_set_name / npc_set_name.
talk_effect_fun_t::func f_set_name( const JsonObject &jo, std::string_view member,
                                    std::string_view, bool is_npc )
{
    JsonObject jobj = jo.get_object( member );
    std::optional<str_or_var> full;
    std::optional<str_or_var> first;
    std::optional<str_or_var> last;
    if( jobj.has_member( "full" ) ) {
        full = get_str_or_var( jobj.get_member( "full" ), "full" );
    }
    if( jobj.has_member( "first" ) ) {
        first = get_str_or_var( jobj.get_member( "first" ), "first" );
    }
    if( jobj.has_member( "last" ) ) {
        last = get_str_or_var( jobj.get_member( "last" ), "last" );
    }
    const bool last_from_other = jobj.get_bool( "last_from_other", false );
    return [is_npc, full, first, last, last_from_other]( dialogue const & d ) {
        Character *ch = d.actor( is_npc )->get_character();
        if( ch == nullptr ) {
            return;
        }
        const auto split = []( const std::string & s ) -> std::pair<std::string, std::string> {
            const size_t at = s.find_last_of( ' ' );
            if( at == std::string::npos ) {
                return { s, std::string() };
            }
            return { s.substr( 0, at ), s.substr( at + 1 ) };
        };
        std::pair<std::string, std::string> parts = split( ch->get_name() );
        if( full ) {
            const std::string f = full->evaluate( d );
            if( !f.empty() ) {
                parts = split( f );
            }
        }
        if( first ) {
            const std::string f = first->evaluate( d );
            if( !f.empty() ) {
                parts.first = f;
            }
        }
        if( last ) {
            const std::string l = last->evaluate( d );
            if( !l.empty() ) {
                parts.second = l;
            }
        }
        if( last_from_other && d.has_actor( !is_npc ) ) {
            Character *other = d.actor( !is_npc )->get_character();
            if( other != nullptr ) {
                const std::string l = split( other->get_name() ).second;
                if( !l.empty() ) {
                    parts.second = l;
                }
            }
        }
        const std::string result = parts.second.empty() ? parts.first : parts.first + " " + parts.second;
        if( !result.empty() ) {
            ch->name = result;
            ch->play_name = result;
        }
    };
}

talk_effect_fun_t::func f_lose_morale( const JsonObject &jo, std::string_view member,
                                       std::string_view, bool is_npc )
{''', "u_set_name / npc_set_name.")

patch("npctalk.cpp",
      '''    { "u_lose_morale", "npc_lose_morale", jarg::member, &talk_effect_fun::f_lose_morale },''',
      '''    { "u_lose_morale", "npc_lose_morale", jarg::member, &talk_effect_fun::f_lose_morale },
    // People First
    { "u_set_name", "npc_set_name", jarg::object, &talk_effect_fun::f_set_name },''',
      "&talk_effect_fun::f_set_name")

# ---------------------------------------------------------------- 3. let-me-pass cooldown, 4. no pulping for CANNOT_ATTACK
patch("npcmove.cpp",
      '''static const json_character_flag json_flag_CANNOT_ATTACK( "CANNOT_ATTACK" );''',
      '''static const json_character_flag json_flag_CANNOT_ATTACK( "CANNOT_ATTACK" );

// People First: the "let me pass" bark at most once a minute per NPC (in crowds with walk orders it fired every turn).
static std::map<int, time_point> pf_let_me_pass_last;
static bool pf_may_say_let_me_pass( const npc &who )
{
    const int key = who.getID().get_value();
    const auto it = pf_let_me_pass_last.find( key );
    if( it != pf_let_me_pass_last.end() && calendar::turn - it->second < 1_minutes ) {
        return false;
    }
    pf_let_me_pass_last[key] = calendar::turn;
    return true;
}''', "the \"let me pass\" bark at most once a minute")

# playtest 3: once a minute was still dozens of barks in a 3-hour wait (one person stuck behind visitors in a corridor)
patch("npcmove.cpp",
      '''calendar::turn - it->second < 1_minutes ) {''',
      '''calendar::turn - it->second < 15_minutes ) { // People First: 15 minutes (playtest 3)''',
      "15 minutes (playtest 3)")

# 17. full run (11 people in one evac shelter, a band's camp): once per 15 minutes per person was still a bark every few
# minutes, and the household's own lines scrolled out of the log.  One shared limit on top: anyone, at most every 10 minutes.
patch("npcmove.cpp",
      '''    pf_let_me_pass_last[key] = calendar::turn;
    return true;''',
      '''    static time_point pf_let_me_pass_any = calendar::before_time_starts; // People First (patch 17): one for everyone
    if( calendar::turn - pf_let_me_pass_any < 10_minutes ) {
        return false;
    }
    pf_let_me_pass_any = calendar::turn;
    pf_let_me_pass_last[key] = calendar::turn;
    return true;''', "People First (patch 17)")

# playtest 3: a walk order (u_set_guard_pos) to the tile you stand on never ended; the NPC waited behind you for hours
patch("npcmove.cpp",
      '''            if( pos_bub() == local_guard_pos || path.empty() ) {''',
      '''            // People First: a walk order to a tile someone else stands on ends next to it.
            const Creature *pf_occupant = get_creature_tracker().creature_at( local_guard_pos );
            if( pos_bub() == local_guard_pos || path.empty() ||
                ( pf_occupant != nullptr && pf_occupant != this && rl_dist( pos_bub(), local_guard_pos ) <= 1 ) ) {''',
      "a walk order to a tile someone else stands on ends next to it")

def patch_all(fname, anchor, replacement, marker, expect):
    p = root / fname
    s = p.read_text(encoding="utf-8")
    if marker in s:
        print(f"  {fname}: already has '{marker}'")
        return
    n = s.count(anchor)
    if n != expect:
        raise SystemExit(f"{fname}: anchor found {n} times (expected {expect}): {anchor[:80]!r}")
    p.write_text(s.replace(anchor, replacement), encoding="utf-8", newline="\n")
    print(f"  {fname}: applied '{marker}' x{n}")

# full run: vanilla's "<npcname> wields a %s." goes through add_msg_if_player_sees, which never fills the tag; our
# defense patches make NPCs switch weapons more often, so the raw tag showed up in the log
patch_all("npc.cpp",
          '''add_msg_if_player_sees( *this, m_info, _( "<npcname> wields a %s." ),
                                get_wielded_item()->tname() );''',
          '''add_msg_if_player_sees( *this, m_info, _( "%1$s wields a %2$s." ), /* People First: wields name */
                                get_name(), get_wielded_item()->tname() );''',
          "People First: wields name", 2)

# 13. full run: a shot's overshoot (continue_line past the target) can run off the edge of the reality bubble, and vanilla
# raises a debugmsg error screen for every such shot.  With patches 6-8 our people fight near the edge of the bubble, so
# it came up repeatedly.  The shot just leaves the map; the line goes to the ballistics debug channel.
patch("ballistics.cpp",
      '''                debugmsg( "Shot along %s out-of-bounds", tp.to_string() );''',
      '''                // People First: a shot leaving the map is expected
                add_msg_debug( debugmode::DF_BALLISTIC, "Shot along %s out-of-bounds", tp.to_string() );''',
      "People First: a shot leaving the map is expected")

patch_all("npcmove.cpp",
          '''say( chat_snippets().snip_let_me_pass.translated() );''',
          '''if( pf_may_say_let_me_pass( *this ) ) { /* People First: rate-limited */ say( chat_snippets().snip_let_me_pass.translated() ); }''',
          "People First: rate-limited", 2)

patch("npcmove.cpp",
      '''bool npc::find_corpse_to_pulp()
{
    map &here = get_map();
''',
      '''bool npc::find_corpse_to_pulp()
{
    map &here = get_map();
    // People First: children and babies (CANNOT_ATTACK) don't go pulping corpses.
    if( has_flag( json_flag_CANNOT_ATTACK ) ) {
        return false;
    }
''', "children and babies (CANNOT_ATTACK) don't go pulping")

# ---------------------------------------------------------------- 5. swap places with PF_SWAP NPCs
patch("avatar_action.cpp",
      '''static const json_character_flag json_flag_CANNOT_ATTACK( "CANNOT_ATTACK" );''',
      '''static const json_character_flag json_flag_CANNOT_ATTACK( "CANNOT_ATTACK" );
// People First: NPCs with this flag swap places when you walk into them.  The flag is defined by the mod.
static const json_character_flag json_flag_PF_SWAP( "PF_SWAP" );''', "NPCs with this flag swap places")

patch("avatar_action.cpp",
      '''        if( !np.is_enemy() ) {
            g->npc_menu( np );
            return false;
        }''',
      '''        if( !np.is_enemy() ) {
            // People First: people of the mod (PF_SWAP) step aside instead of opening the NPC menu,
            // whose next keypress could be "attack".
            if( np.has_flag( json_flag_PF_SWAP ) && you.get_grab_type() == object_type::NONE ) {
                add_msg( _( "You swap places with %s." ), np.get_name() );
                g->swap_critters( you, np );
                you.mod_moves( -you.get_speed() );
                return false;
            }
            g->npc_menu( np );
            return false;
        }''', "people of the mod (PF_SWAP) step aside")
# ---------------------------------------------------------------- 6. stand up for the people you're bonded to
patch("npcmove.cpp",
      '''#include "creature.h"
''',
      '''#include "creature.h"
#include "global_vars.h" // People First: bonded defense
#include "math_parser_diag_value.h"
''', "People First: bonded defense")

patch("npcmove.cpp",
      '''    pf_let_me_pass_last[key] = calendar::turn;
    return true;
}''',
      '''    pf_let_me_pass_last[key] = calendar::turn;
    return true;
}

// People First: NPCs stand up for the people they're bonded to.  Vanilla only defends faction mates who "watch your
// back", and the mod's people are lone wolves (no_faction), so nobody defended anybody.  The bonds are the mod's
// character variables: kin (pf_mom / pf_dad / pf_guardian / pf_sweet hold uids), the same band (pf_band), the same
// household (pf_resident), or warmth (pf_v_<uid>_w) at or above the global pf_defend_w (default 40, the mod's "close
// friend").  The global pf_set_defend = 0 turns it off.  NPCs without a pf_uid are untouched.
static std::string pf_str_var( const Creature &c, const std::string &key )
{
    const diag_value *v = c.maybe_get_value( key );
    return v != nullptr && v->is_str() ? v->str() : std::string();
}
static double pf_num_var( const Creature &c, const std::string &key )
{
    const diag_value *v = c.maybe_get_value( key );
    return v != nullptr && v->is_dbl() ? v->dbl() : 0.0;
}
static double pf_global_num( const std::string &key, double def )
{
    const diag_value *v = get_globals().maybe_get_global_value( key );
    return v != nullptr && v->is_dbl() ? v->dbl() : def;
}
static bool pf_protects( const npc &me, const Character &other )
{
    const std::string my_uid = pf_str_var( me, "pf_uid" );
    const std::string other_uid = other.is_avatar() ? std::string( "AVATAR" ) : pf_str_var( other, "pf_uid" );
    if( my_uid.empty() || other_uid.empty() || pf_global_num( "pf_set_defend", 1.0 ) == 0.0 ) {
        return false;
    }
    for( const char *kin : { "pf_mom", "pf_dad", "pf_guardian" } ) {
        if( pf_str_var( other, kin ) == my_uid || pf_str_var( me, kin ) == other_uid ) {
            return true;
        }
    }
    if( pf_num_var( me, "pf_has_sweet" ) == 1.0 && pf_str_var( me, "pf_sweet" ) == other_uid ) {
        return true;
    }
    if( pf_num_var( me, "pf_resident" ) == 1.0 && ( other.is_avatar() ||
            pf_num_var( other, "pf_resident" ) == 1.0 ) ) {
        return true;
    }
    const double band = pf_num_var( me, "pf_band" );
    if( !other.is_avatar() && band > 0.0 && pf_num_var( other, "pf_band" ) == band ) {
        return true;
    }
    return pf_num_var( me, "pf_v_" + other_uid + "_w" ) >= pf_global_num( "pf_defend_w", 40.0 );
}''', "NPCs stand up for the people they're bonded to")

patch("npcmove.cpp",
      '''        if( has_faction_relationship( guy, npc_factions::relationship::watch_your_back ) ) {
            ai_cache.friends.emplace_back( g->shared_from( guy ) );''',
      '''        if( has_faction_relationship( guy, npc_factions::relationship::watch_your_back ) ||
            pf_protects( *this, guy ) ) { // People First: or someone we're bonded to
            ai_cache.friends.emplace_back( g->shared_from( guy ) );''', "or someone we're bonded to")

patch("npcmove.cpp",
      '''    if( is_friendly( player_character ) && sees_player ) {
        ai_cache.friends.emplace_back( g->shared_from( player_character ) );''',
      '''    if( ( is_friendly( player_character ) || ( !is_enemy() &&
            pf_protects( *this, player_character ) ) ) && sees_player ) { // People First: bonded to you
        ai_cache.friends.emplace_back( g->shared_from( player_character ) );''', "People First: bonded to you")

# ---------------------------------------------------------------- 7. follower rules only for followers
# Every NPC is born with the follower rule follow_close, and assess_danger applied it to non-followers too: an NPC more than
# 4 tiles from the player had must_retreat set and skipped every monster (found with the trace below, 2026-10-11).
patch("npcmove.cpp",
      '''    int friendly_count = 1; // count yourself as a friendly
    int def_radius = rules.has_flag( ally_rule::follow_close ) ? follow_distance() : 6;''',
      '''    int friendly_count = 1; // count yourself as a friendly
    // People First: follower rules (stay close to the player) only bind followers.
    const bool pf_follows_close = is_player_ally() && rules.has_flag( ally_rule::follow_close );
    int def_radius = pf_follows_close ? follow_distance() : 6;''', "follower rules (stay close to the player) only bind followers")
patch("npcmove.cpp",
      '''    const bool must_retreat = rules.has_flag( ally_rule::follow_close ) &&''',
      '''    const bool must_retreat = pf_follows_close &&''', "const bool must_retreat = pf_follows_close")

# ---------------------------------------------------------------- 8. close in before attacking
# Once our people target distant monsters (patches 6-7), vanilla's attack code assumes the target is near: a pistol at 25
# tiles aims forever, and a Magiclysm caster at 19 tiles spun until the infinite-loop guard fired (test 2026-10-11).
patch("npcmove.cpp",
      '''    add_msg_debug( debugmode::DF_NPC, "%s chose action %s.", get_name(), npc_action_name( action ) );''',
      '''    add_msg_debug( debugmode::DF_NPC, "%s chose action %s.", get_name(), npc_action_name( action ) );
    // People First: close in.  One of our people whose target is beyond the range they can use walks toward it first.
    if( action == npc_do_attack && !pf_str_var( *this, "pf_uid" ).empty() && current_target() != nullptr &&
        !has_flag( json_flag_CANNOT_MOVE ) ) {
        const tripoint_bub_ms tpos = current_target()->pos_bub();
        const int reach = std::max( confident_range_cache.value_or( 1 ), 1 );
        if( rl_dist( pos_bub(), tpos ) > reach + 1 ) {
            update_path( tpos );
            if( !path.empty() ) {
                ai_cache.current_attack.reset();
                ai_cache.current_attack_evaluation = npc_attack_rating{};
                if( pf_global_num( "pf_debug_defend", 0.0 ) == 1.0 ) {
                    DebugLog( D_WARNING, D_MAIN ) << "PF defend: " << get_name() << " closes in (dist "
                                                  << rl_dist( pos_bub(), tpos ) << ", reach " << reach << ")";
                }
                move_to_next();
                return;
            }
        }
    }''', "People First: close in.")

# ---------------------------------------------------------------- 9. who ran
# JSON can't see an NPC flee (vanilla's npc_run_away lasts a few turns).  When one of our people breaks into a flat-out
# retreat, stamp pf_fled_t (same units as JSON time('now')); the mod's Reckoning reads it once it's calm.
patch("npcmove.cpp",
      '''                add_msg_debug( debugmode::DF_NPC_COMBATAI, "%s upgrades reposition to flat out retreat.", name );''',
      '''                add_msg_debug( debugmode::DF_NPC_COMBATAI, "%s upgrades reposition to flat out retreat.", name );
                // People First: remember that they ran (Reckoning).
                if( !pf_str_var( *this, "pf_uid" ).empty() ) {
                    set_value( "pf_fled_t", diag_value{ to_turns<double>( calendar::turn - calendar::turn_zero ) } );
                    get_globals().set_global_value( "pf_rk_need", diag_value{ 1.0 } ); // the calm-time pass judges it
                    if( pf_global_num( "pf_debug_defend", 0.0 ) == 1.0 ) {
                        DebugLog( D_WARNING, D_MAIN ) << "PF defend: " << get_name() << " breaks and runs (pf_fled_t)";
                    }
                }''', "People First: remember that they ran")

# ---------------------------------------------------------------- 10. a People key
# A real input action ("people_first", default key ',' via data/raw/keybindings.json, see engine/install_data.py) that
# opens the mod's menu (EOC PF_open_menu) in one keypress instead of the mutations menu plus a letter.  Rebindable in the
# game's keybinding screen like any other action; listed in the action menu under Misc.
patch("action.h",
      '''    /** Toggle timing of the game hours */
    ACTION_TOGGLE_HOUR_TIMER,''',
      '''    /** Toggle timing of the game hours */
    ACTION_TOGGLE_HOUR_TIMER,
    /** People First: open the People menu (runs the mod's EOC PF_open_menu) */
    ACTION_PEOPLE_FIRST,''', "People First: open the People menu")
patch("action.cpp",
      '''        case ACTION_MUTATIONS:
            return "mutations";''',
      '''        case ACTION_MUTATIONS:
            return "mutations";
        case ACTION_PEOPLE_FIRST: // People First
            return "people_first";''', "case ACTION_PEOPLE_FIRST: // People First")
patch("action.cpp",
      '''            REGISTER_ACTION( ACTION_MUTATIONS );''',
      '''            REGISTER_ACTION( ACTION_MUTATIONS );
            REGISTER_ACTION( ACTION_PEOPLE_FIRST ); // People First''', "REGISTER_ACTION( ACTION_PEOPLE_FIRST )")
patch("game.cpp",
      '''    ctxt.register_action( "mutations" );''',
      '''    ctxt.register_action( "mutations" );
    ctxt.register_action( "people_first" ); // People First''', 'ctxt.register_action( "people_first" )')
patch("handle_action.cpp",
      '''#include "avatar.h"
''',
      '''#include "avatar.h"
#include "dialogue.h" // People First: the People key
#include "effect_on_condition.h"
#include "talker.h"
''', "People First: the People key")
patch("handle_action.cpp",
      '''        case ACTION_MUTATIONS:
            player_character.power_mutations();
            break;''',
      '''        case ACTION_MUTATIONS:
            player_character.power_mutations();
            break;

        case ACTION_PEOPLE_FIRST: { // People First: the People menu in one keypress
            const effect_on_condition_id pf_menu( "PF_open_menu" );
            if( pf_menu.is_valid() ) {
                dialogue d( get_talker_for( get_avatar() ), nullptr );
                pf_menu->activate( d );
            } else {
                add_msg( m_info, _( "The People First mod isn't loaded in this world." ) );
            }
            break;
        }''', "People First: the People menu in one keypress")

# ---------------------------------------------------------------- 11. the fork's own title screen
# The main menu shows data/title/people_first.title (engine/make_title.py; installed by engine/install_data.py) when it
# exists, ahead of the vanilla, alternate and seasonal arts, and prints "People First" under the version line.  The
# official exe never reads that file, so it keeps the vanilla title.
patch("path_info.cpp",
      '''    if( !get_option<bool>( "ENABLE_ASCII_TITLE" ) ) {
        return _( "Cataclysm: Dark Days Ahead" );
    }
''',
      '''    if( !get_option<bool>( "ENABLE_ASCII_TITLE" ) ) {
        return _( "Cataclysm: Dark Days Ahead" );
    }

    // People First: the fork's own title art, ahead of the alternate and seasonal ones
    if( file_exist( theme_basepath + "people_first.title" ) ) {
        return theme_basepath + "people_first.title";
    }
''', "People First: the fork's own title art")
patch("main_menu.cpp",
      '''    center_print( w_open, iLine, c_light_blue, string_format( _( "Version: 0.I (Ito) Stable Release" ),
                  getVersionString() ) );
''',
      '''    center_print( w_open, iLine, c_light_blue, string_format( _( "Version: 0.I (Ito) Stable Release" ),
                  getVersionString() ) );
    // People First: the fork's name under the version line (only where it can't run into the menu bar)
    if( iLine + 1 < getmaxy( w_open ) - 4 ) {
        center_print( w_open, iLine + 1, c_light_cyan, "People First" );
    }
''', "People First: the fork's name under the version line")

# ---------------------------------------------------------------- 14. hearing the fight in the dark
# Full run day 101 and 122: an amalgamation and a woodland wight attacked the player indoors at night, in fog, and Mitzi (4
# tiles), the household and the children were all "Ignoring" it.  assess_danger skips any monster the NPC can't see, and
# keeps the player as a friend only if seen.  In a dark room you still hear someone being torn apart next to you.
patch("npcmove.cpp",
      '''    return pf_num_var( me, "pf_v_" + other_uid + "_w" ) >= pf_global_num( "pf_defend_w", 40.0 );
}''',
      '''    return pf_num_var( me, "pf_v_" + other_uid + "_w" ) >= pf_global_num( "pf_defend_w", 40.0 );
}
// People First (patch 14): what you hear in the dark.  A protected person within 10 tiles (no wall between) is known
// without seeing them; so is a hostile monster within 3 tiles, or one right next to someone we protect.
static bool pf_near_protected( const npc &me, const Character &other )
{
    return !pf_str_var( me, "pf_uid" ).empty() && rl_dist( me.pos_bub(), other.pos_bub() ) <= 10 &&
           get_map().has_potential_los( me.pos_bub(), other.pos_bub() ) && pf_protects( me, other );
}
static bool pf_hears_fight( const npc &me, const monster &critter )
{
    if( pf_str_var( me, "pf_uid" ).empty() || pf_global_num( "pf_set_defend", 1.0 ) == 0.0 ) {
        return false;
    }
    const int d = rl_dist( me.pos_bub(), critter.pos_bub() );
    if( d <= 3 ) {
        return true;
    }
    if( d > 12 ) {
        return false;
    }
    const Character &you = get_player_character();
    if( rl_dist( you.pos_bub(), critter.pos_bub() ) <= 1 && pf_near_protected( me, you ) ) {
        return true;
    }
    for( const npc &guy : g->all_npcs() ) {
        if( &guy != &me && rl_dist( guy.pos_bub(), critter.pos_bub() ) <= 1 && pf_near_protected( me, guy ) ) {
            return true;
        }
    }
    return false;
}''', "People First (patch 14): what you hear in the dark")
patch("npcmove.cpp",
      '''            pf_protects( *this, player_character ) ) ) && sees_player ) { // People First: bonded to you''',
      '''            pf_protects( *this, player_character ) ) ) && ( sees_player ||
                    pf_near_protected( *this, player_character ) ) ) { // People First: bonded to you (seen or heard)''',
      "bonded to you (seen or heard)")
patch("npcmove.cpp",
      '''        if( !sees( here, critter ) ) {
            continue;
        }

        ai_cache.hostile_guys.emplace_back( g->shared_from( critter ) );''',
      '''        if( !sees( here, critter ) && !pf_hears_fight( *this, critter ) ) { // People First: or hears it
            continue;
        }

        ai_cache.hostile_guys.emplace_back( g->shared_from( critter ) );''', "People First: or hears it")

# 14b. In the dark, close in.  KinfoldLab test (2026-10-14): with patch 14 Mitzi targeted the zombie biting the player in
# the dark (hostiles=1, action=Attack) but never fired: a gun can't be aimed at something you can't see, and at 5-8 tiles she
# was inside her rifle's range, so patch 8 never walked her in.  An unseen target more than a tile away: walk up to it.
patch("npcmove.cpp",
      '''        if( rl_dist( pos_bub(), tpos ) > reach + 1 ) {
            update_path( tpos );''',
      '''        if( rl_dist( pos_bub(), tpos ) > reach + 1 || // People First: in the dark, close in
            ( rl_dist( pos_bub(), tpos ) > 1 && !sees( get_map(), *current_target() ) ) ) {
            update_path( tpos );''', "People First: in the dark, close in")

# ---------------------------------------------------------------- 15. moved items lose their old owner
# The mod's housekeeping teleports items (food back to the stores, a dead resident's things).  A dead person's canned beans
# kept their faction owner, and the player was asked "considered stealing" for the household's own food (full run).
patch("npctalk.cpp",
      '''        if( it && it->get_item() ) {
            map_add_item( *it->get_item(), target_pos );''',
      '''        if( it && it->get_item() ) {
            // People First (patch 15): what's been tidied away belongs to the household now.
            item pf_moved = *it->get_item();
            pf_moved.remove_owner();
            map_add_item( pf_moved, target_pos );''', "People First (patch 15)")

# ---------------------------------------------------------------- 16. items answer "is it rotten?" and "is it a zombie's corpse?"
# JSON can read an item's flags (npc_has_flag on the beta item in u_map_run_item_eocs) but not its rot or what a corpse was.
# The stores kept rotten cabbage forever, and corpses couldn't be hauled out because one of ours might be among them (full run).
# Pseudo-flags: PF_ROTTEN (the item, or food inside it, is rotten), PF_GOING_BAD (90% of shelf life), PF_ZOMBIE_CORPSE.
patch("talker_item.cpp", '''#include "messages.h"''', '''#include "messages.h"
#include "mtype.h" // People First (patch 16) include''', "People First (patch 16) include")
patch("talker_item.cpp",
      '''static const ammotype ammo_battery( "battery" );''',
      '''static const ammotype ammo_battery( "battery" );
static const species_id species_ZOMBIE_pf( "ZOMBIE" ); // People First (patch 16)

static bool pf_item_pseudo_flag( const item &it, const std::string &f, bool &answer )
{
    if( f == "PF_ROTTEN" || f == "PF_GOING_BAD" ) {
        const bool rotten = f == "PF_ROTTEN";
        auto bad = [rotten]( const item & i ) {
            return i.goes_bad() && ( rotten ? i.rotten() : i.is_going_bad() );
        };
        answer = bad( it );
        if( !answer ) {
            for( const item *c : it.all_items_top() ) {
                if( bad( *c ) ) {
                    answer = true;
                    break;
                }
            }
        }
        return true;
    }
    if( f == "PF_ZOMBIE_CORPSE" ) {
        answer = it.is_corpse() && it.get_mtype() != nullptr && it.get_mtype()->in_species( species_ZOMBIE_pf );
        return true;
    }
    return false;
}''', "static bool pf_item_pseudo_flag")
patch("talker_item.cpp",
      '''                   f.c_str() );
    return me_it_const->get_item()->has_flag( f );''',
      '''                   f.c_str() );
    bool pf_answer = false; // People First (patch 16): pseudo-flags
    if( pf_item_pseudo_flag( *me_it_const->get_item(), f.str(), pf_answer ) ) {
        return pf_answer;
    }
    return me_it_const->get_item()->has_flag( f );''', "People First (patch 16): pseudo-flags")

# ---------------------------------------------------------------- 18. children run to a grown-up
# Full run day 151: Taunya (16, a child of the household) was set on by a skeletal dog 15 tiles from home in daylight, fled
# the vanilla way (any direction away from the threat), ended up 58 tiles out in open ground and died.  Vanilla only lets the
# player's followers "run to a friend" (the player).  A People First child who flees runs to the nearest grown-up they're
# bonded to (ai_cache.friends: kin, household, band, close friends, you) within 30 tiles.
patch("npcmove.cpp",
      """    add_msg_debug( debugmode::DF_NPC_MOVEAI,
                   "<color_brown>good_escape_direction</color> activated by %s", name );
""",
      """    add_msg_debug( debugmode::DF_NPC_MOVEAI,
                   "<color_brown>good_escape_direction</color> activated by %s", name );
    // People First (patch 18): a child runs to the nearest grown-up who looks after them, not off into the open.
    static const trait_id pf_trait_child( "PF_CHILD" );
    if( has_trait( pf_trait_child ) && path.empty() ) {
        const Creature *pf_best = nullptr;
        int pf_best_d = 31;
        for( const weak_ptr_fast<Creature> &guy : ai_cache.friends ) {
            const shared_ptr_fast<Creature> c = guy.lock();
            const Character *ch = c ? c->as_character() : nullptr;
            if( ch == nullptr || ch == this || ch->is_dead_state() || ch->has_trait( pf_trait_child ) ) {
                continue;
            }
            const int d = rl_dist( pos_bub(), ch->pos_bub() );
            if( d < pf_best_d ) {
                pf_best_d = d;
                pf_best = ch;
            }
        }
        if( pf_best != nullptr && pf_best_d > 1 ) {
            update_path( pf_best->pos_bub() );
            if( !path.empty() ) {
                return path[0];
            }
        }
    }
""", "People First (patch 18)")

# ---------------------------------------------------------------- 19. running from monsters isn't running from you
# Full run day 151: an amalgamation swarm made Fernando and Consuelo (Golly Whitmore's band) panic.  For a non-follower,
# vanilla's panic also sets NPCATT_FLEE_TEMP, which adds npc_flee_player for 24 hours: they counted as enemies and ran from
# the player all day, bleeding, 50 tiles off.  People First NPCs flee the monsters (npc_run_away, timed) and nothing more;
# anyone already stuck in that state drops it once the panic is over.
patch("npcmove.cpp",
      """                warn_about( "run_away", run_away_for );
                if( !is_player_ally() ) {
                    set_attitude( NPCATT_FLEE_TEMP );
                }""",
      """                warn_about( "run_away", run_away_for );
                // People First (patch 19): our people run from the monsters, not from you for a day.
                if( !is_player_ally() && pf_str_var( *this, "pf_uid" ).empty() ) {
                    set_attitude( NPCATT_FLEE_TEMP );
                }""", "People First (patch 19): our people run")
patch("npcmove.cpp",
      """    if( attitude == NPCATT_FLEE ) {
        set_attitude( NPCATT_FLEE_TEMP );  // Only run for so many hours
    } else if( attitude == NPCATT_FLEE_TEMP && !has_effect( effect_npc_flee_player ) ) {""",
      """    // People First (patch 19): a panic from before the fix (or any other) is over once they've stopped running.
    if( attitude == NPCATT_FLEE_TEMP && !pf_str_var( *this, "pf_uid" ).empty() &&
        !has_effect( effect_npc_run_away ) && !guaranteed_hostile() ) {
        remove_effect( effect_npc_flee_player );
    }
    if( attitude == NPCATT_FLEE ) {
        set_attitude( NPCATT_FLEE_TEMP );  // Only run for so many hours
    } else if( attitude == NPCATT_FLEE_TEMP && !has_effect( effect_npc_flee_player ) ) {""", "a panic from before the fix")

# ---------------------------------------------------------------- 20. no flight from you unless you hurt them
# Full run day 151: after patch 19, Consuelo (Golly's band) still flipped to NPCATT_FLEE_TEMP when Dante walked up, shouted
# "A maniac northwest, near enough to see us" (the bark for a player they count as an enemy) and ran 50 tiles.  More than
# one vanilla path sets it.  A People First NPC only takes a flee attitude if you actually hit them (hit_by_player) or
# their faction is hostile; one already in it drops it at once (they still run from monsters through npc_run_away).
patch("npc.cpp",
      """void npc::set_attitude( npc_attitude new_attitude )
{
    const map &here = get_map();
""",
      """void npc::set_attitude( npc_attitude new_attitude )
{
    const map &here = get_map();
    // People First (patch 20): our people don't take flight from you unless you hurt them.
    if( ( new_attitude == NPCATT_FLEE || new_attitude == NPCATT_FLEE_TEMP ) && !hit_by_player &&
        !guaranteed_hostile() ) {
        const diag_value *pf_uid = maybe_get_value( "pf_uid" );
        if( pf_uid != nullptr && pf_uid->is_str() && !pf_uid->str().empty() ) {
            return;
        }
    }
""", "People First (patch 20): our people don't take flight")
patch("npc.cpp",
      """#include "dialogue.h"
""",
      """#include "dialogue.h"
#include "math_parser_diag_value.h" // People First (patch 20) include
""", "People First (patch 20) include")
patch("npcmove.cpp",
      """        !has_effect( effect_npc_run_away ) && !guaranteed_hostile() ) {
        remove_effect( effect_npc_flee_player );""",
      """        !hit_by_player && !guaranteed_hostile() ) { // People First (patch 20): at once, unless you hurt them
        remove_effect( effect_npc_flee_player );""", "!hit_by_player && !")

# 20b. guaranteed_hostile() is true for anyone already fleeing (it includes is_enemy()), so patch 20's clear never fired
# (Fernando and Consuelo stayed "Fleeing").  Only a hostile faction keeps the flight.
patch("npcmove.cpp",
      """        !hit_by_player && !guaranteed_hostile() ) { // People First (patch 20): at once, unless you hurt them""",
      """        !hit_by_player && !( my_fac && my_fac->likes_u < -10 ) ) { // People First (patch 20b): at once, unless you hurt them""",
      "People First (patch 20b): at once")
patch("npc.cpp",
      """    if( ( new_attitude == NPCATT_FLEE || new_attitude == NPCATT_FLEE_TEMP ) && !hit_by_player &&
        !guaranteed_hostile() ) {""",
      """    if( ( new_attitude == NPCATT_FLEE || new_attitude == NPCATT_FLEE_TEMP ) && !hit_by_player &&
        !( my_fac && my_fac->likes_u < -10 ) ) { // People First (patch 20b)""",
      "People First (patch 20b)")

# ---------------------------------------------------------------- 21. a teleported NPC is there at once
# Full run day 152 (and Town pass 3): an off-screen NPC teleported into the reality bubble (a newcomer, a stray coming home)
# stayed inactive until the map shifted: missing from every scan, invisible, unreachable.  Marylin Whitmore stood at home
# for hours while People said "last saw 11 map tiles east".  After teleporting an NPC to a spot inside the bubble, load it.
patch("teleport.cpp",
      """    if( c_is_u ) {
        g->place_player( p->pos_bub() );
        g->update_map( *p );
    }""",
      """    if( c_is_u ) {
        g->place_player( p->pos_bub() );
        g->update_map( *p );
    } else if( p != nullptr && here.inbounds( target ) ) {
        g->load_npcs(); // People First (patch 21): an NPC teleported into the bubble is active at once
    }""", "People First (patch 21)")

# ---------------------------------------------------------------- 22. our people walk around deep water
# Full run day 158: Emanuel Ceballos's band, heading west on-screen, stood in flowing deep water west of the walls with a child
# (Enrique) in tow; earlier in the run a beaver hidden in the river killed a band child.  The band picks dry walk targets, but
# vanilla pathing treats deep water as merely slow, so any target across a river routes through it.  A People First NPC's
# path avoids deep water unless they're already in it (then they may path out); no dry route means no walk this time.
patch("npc.cpp",
      """std::function<bool( const tripoint_bub_ms & )> npc::get_path_avoid() const
{
    return [this]( const tripoint_bub_ms & p ) {""",
      """std::function<bool( const tripoint_bub_ms & )> npc::get_path_avoid() const
{
    // People First (patch 22): our people go around deep water unless they're already in it.
    const diag_value *pf_uid_v = maybe_get_value( "pf_uid" );
    const bool pf_dry = pf_uid_v != nullptr && pf_uid_v->is_str() && !pf_uid_v->str().empty() &&
                        !get_map().has_flag( ter_furn_flag::TFLAG_DEEP_WATER, pos_bub() );
    return [this, pf_dry]( const tripoint_bub_ms & p ) {""", "People First (patch 22): our people go around")
patch("npc.cpp",
      """        if( here.is_open_air( p ) ) {
            return true;
        }
        if( rules.has_flag( ally_rule::hold_the_line ) &&""",
      """        if( here.is_open_air( p ) ) {
            return true;
        }
        if( pf_dry && here.has_flag( ter_furn_flag::TFLAG_DEEP_WATER, p ) ) { // People First (patch 22) avoid
            return true;
        }
        if( rules.has_flag( ally_rule::hold_the_line ) &&""", "People First (patch 22) avoid")

# ---------------------------------------------------------------- 23. a shared meal is eaten, not injected
# Full run days 151-160: a shared meal added half the food's calories and vitamins straight to the body, so the stomach stayed
# empty: "Hungry" right after the meal, and the eat menu's "Consumed today" read 0 kcal.  u_pf_eat_share() = P puts P percent
# of the other talker (a food item) into u's stomach exactly as eating does; it digests from there.  JSON calls it only from
# people_first_engine (the stock exe doesn't know the function).
patch("math_parser_diag.cpp",
      """double weight_eval( const_dialogue const &d, char scope,""",
      """// People First (patch 23): u_pf_eat_share() = P, P percent of the item into u's stomach.
double pf_eat_share_eval( const_dialogue const &, char, std::vector<diag_value> const &, diag_kwargs const & )
{
    return 0.0;
}

void pf_eat_share_ass( double val, dialogue &d, char scope, std::vector<diag_value> const &, diag_kwargs const & )
{
    Character *ch = d.actor( is_beta( scope ) )->get_character();
    item_location *it = d.actor( !is_beta( scope ) )->get_item();
    if( ch == nullptr || it == nullptr || !*it || !( *it )->is_comestible() ) {
        return;
    }
    const item &food = **it;
    const double f = std::clamp( val, 0.0, 100.0 ) / 100.0;
    nutrients n = ch->compute_effective_nutrients( food );
    n *= f;
    const std::pair<units::volume, units::volume> vol = ch->masticated_volume( food );
    food_summary ingested{ vol.first * f, vol.second * ( ch->compute_effective_food_volume_ratio( food ) * f ), n };
    ch->stomach.ingest( ingested );
    if( ch->is_avatar() ) {
        get_avatar().add_ingested_kcal( ingested.nutr.calories / 1000 );
    }
    for( const auto &v : ingested.nutr.vitamins() ) {
        ch->daily_vitamins[v.first].first += v.second;
    }
}

double weight_eval( const_dialogue const &d, char scope,""", "People First (patch 23): u_pf_eat_share")
patch("math_parser_diag.cpp",
      """    { "weight", { "un", 0, weight_eval } },""",
      """    { "weight", { "un", 0, weight_eval } },
    { "pf_eat_share", { "un", 0, pf_eat_share_eval, pf_eat_share_ass } }, // People First (patch 23) table""",
      "People First (patch 23) table")
patch("math_parser_diag.cpp",
      """#include "math_parser_diag.h"
""",
      """#include "math_parser_diag.h"
#include "avatar.h" // People First (patch 23) include
""", "People First (patch 23) include")

# 23b. Full run day 180: a shared meal on a full stomach: "Your stomach is full to bursting.  This was a mistake."  Reading
# u_pf_eat_share() now tells JSON how much of the item fits (0-100, percent of one unit), so the meal eats only what fits.
patch("math_parser_diag.cpp",
      """double pf_eat_share_eval( const_dialogue const &, char, std::vector<diag_value> const &, diag_kwargs const & )
{
    return 0.0;
}""",
      """double pf_eat_share_eval( const_dialogue const &d, char scope, std::vector<diag_value> const &, diag_kwargs const & )
{
    // People First (patch 23b): how much of the item (percent of one unit) still fits in u's stomach
    Character const *ch = d.const_actor( is_beta( scope ) )->get_const_character();
    item_location const *it = d.const_actor( !is_beta( scope ) )->get_const_item();
    if( ch == nullptr || it == nullptr || !*it ) {
        return 0.0;
    }
    const units::volume vol = ( *it )->volume() / std::max( 1, ( *it )->count() );
    if( vol <= 0_ml ) {
        return 100.0;
    }
    return std::clamp( 100.0 * units::to_milliliter( ch->stomach.stomach_remaining( *ch ) ) / units::to_milliliter( vol ),
                       0.0, 100.0 );
}""", "People First (patch 23b)")

# ---------------------------------------------------------------- 25. a bigger title
# 2026-10-16 (the user): the People First title art 35% larger (108 x 24).  Vanilla places the art at a fixed offset meant
# for 80 columns.  Center it on its own widest line, and draw only the lines that fit above the version line and the menu.
patch("main_menu.cpp",
      """    if( mmenu_title.size() > 1 ) {
        for( const std::string &i_title : mmenu_title ) {
            nc_color cur_color = c_white;
            nc_color base_color = c_white;
            print_colored_text( w_open, point( iOffsetX, iLine++ ), cur_color, base_color, i_title );
        }
    } else {""",
      """    if( mmenu_title.size() > 1 ) {
        // People First (patch 25): center on the widest line; draw only what fits
        int pf_art_w = 0;
        for( const std::string &i_title : mmenu_title ) {
            pf_art_w = std::max( pf_art_w, utf8_width_notags( i_title.c_str() ) );
        }
        const int pf_off_x = pf_art_w > FULL_SCREEN_WIDTH ? std::max( 0, ( window_width - pf_art_w ) / 2 ) : iOffsetX;
        const int pf_max_lines = std::max( 1, window_height - 8 );
        for( const std::string &i_title : mmenu_title ) {
            if( iLine >= pf_max_lines ) {
                break;
            }
            nc_color cur_color = c_white;
            nc_color base_color = c_white;
            print_colored_text( w_open, point( pf_off_x, iLine++ ), cur_color, base_color, i_title );
        }
    } else {""", "People First (patch 25)")

# ---------------------------------------------------------------- 24. traces for patches 18 and 22 (testing only)
# With the global pf_debug_defend = 1 (Home lab: "Defense: trace"), debug.log gets a "PF flee" line when a People First
# child flees (who they ran to) and a "PF path" line for every new path a People First NPC takes (how many deep-water
# tiles are on it).  Nothing changes in play.
patch("npcmove.cpp",
      """        if( pf_best != nullptr && pf_best_d > 1 ) {
            update_path( pf_best->pos_bub() );""",
      """        if( pf_global_num( "pf_debug_defend", 0.0 ) == 1.0 ) { // People First (patch 24) flee trace
            DebugLog( D_WARNING, D_MAIN ) << "PF flee: " << get_name() << " friends=" << ai_cache.friends.size()
                                          << " runs to=" << ( pf_best ? pf_best->disp_name() : std::string( "nobody" ) )
                                          << " d=" << pf_best_d;
        }
        if( pf_best != nullptr && pf_best_d > 1 ) {
            update_path( pf_best->pos_bub() );""", "People First (patch 24) flee trace")
patch("npcmove.cpp",
      """    while( !new_path.empty() && new_path[0] == pos_bub() ) {
        new_path.erase( new_path.begin() );
    }
""",
      """    while( !new_path.empty() && new_path[0] == pos_bub() ) {
        new_path.erase( new_path.begin() );
    }
    if( pf_global_num( "pf_debug_defend", 0.0 ) == 1.0 && !pf_str_var( *this, "pf_uid" ).empty() ) { // People First (patch 24) path trace
        int pf_deep = 0;
        for( const tripoint_bub_ms &pt : new_path ) {
            pf_deep += get_map().has_flag( ter_furn_flag::TFLAG_DEEP_WATER, pt ) ? 1 : 0;
        }
        DebugLog( D_WARNING, D_MAIN ) << "PF path: " << get_name() << " " << pos_bub().to_string_writable() << " to "
                                      << p.to_string_writable() << " length=" << new_path.size() << " deep_water=" << pf_deep;
    }
""", "People First (patch 24) path trace")

# Trace for testing: with the global pf_debug_defend = 1, every People First NPC's combat decision goes to debug.log.
patch("npcmove.cpp",
      '''    execute_action( action );
}

void npc::execute_action( npc_action action )''',
      '''    // People First: decision trace for testing (global pf_debug_defend = 1).
    if( pf_global_num( "pf_debug_defend", 0.0 ) == 1.0 && !pf_str_var( *this, "pf_uid" ).empty() ) {
        const Creature *t = current_target();
        DebugLog( D_WARNING, D_MAIN ) << "PF defend: " << get_name() << " friends=" << ai_cache.friends.size()
                                      << " hostiles=" << ai_cache.hostile_guys.size() << " target=" << ( t ? t->disp_name() : "none" )
                                      << " danger=" << ai_cache.danger << " enemy=" << mem_combat.assess_enemy
                                      << " ally=" << mem_combat.assess_ally << " att=" << static_cast<int>( attitude )
                                      << " run_away=" << has_effect( effect_npc_run_away ) << " action=" << npc_action_name( action )
                                      << " wield=" << ( get_wielded_item() ? get_wielded_item()->tname() : std::string( "none" ) )
                                      << " dist=" << ( t ? rl_dist( pos_bub(), t->pos_bub() ) : -1 )
                                      << " crange=" << confident_range_cache.value_or( -1 )
                                      << " formation=" << mem_combat.formation_distance << " pos=" << pos_bub().to_string_writable();
    }
    execute_action( action );
    if( pf_global_num( "pf_debug_defend", 0.0 ) == 1.0 && action == npc_do_attack ) {
        DebugLog( D_WARNING, D_MAIN ) << "PF defend: " << get_name() << " after attack: path=" << path.size()
                                      << " moves=" << get_moves() << " pos=" << pos_bub().to_string_writable();
    }
}

void npc::execute_action( npc_action action )''', "decision trace for testing")

print("patch set applied")
