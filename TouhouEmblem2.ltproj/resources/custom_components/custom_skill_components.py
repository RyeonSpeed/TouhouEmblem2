from __future__ import annotations

from app.data.database.components import ComponentType
from app.data.database.database import DB
from app.data.database.skill_components import SkillComponent, SkillTags
from app.engine import (action, banner, combat_calcs, engine, equations,
                        image_mods, item_funcs, item_system, skill_system,
                        target_system)
from app.engine.game_state import game
from app.engine.objects.unit import UnitObject
from app.utilities import utils, static_random
from app.engine.combat import playback as pb
from app.utilities.enums import Strike
from app.events import event_commands, regions, triggers

import logging
import random

class DoNothing(SkillComponent):
    nid = 'do_nothing'
    desc = 'does nothing'
    tag = SkillTags.CUSTOM

    expose = ComponentType.Int
    value = 1
    
class ImmuneNewStatus(SkillComponent):
    nid = 'immune_new_status'
    desc = "Unit is not affected by incoming negative statuses"
    tag = SkillTags.STATUS

    def after_gain_skill(self, unit, other_skill):
        if other_skill.negative:
            action.do(action.RemoveSkill(unit, other_skill))
            
class ImmuneNewChooseStatus(SkillComponent):
    nid = 'immune_new__choose_status'
    desc = "Unit is not affected by incoming negative statuses"
    tag = SkillTags.STATUS
    
    expose = ComponentType.Skill
    value = ''

    def after_gain_skill(self, unit, other_skill):
        if other_skill.nid == self.value:
            if other_skill.negative:
                action.do(action.RemoveSkill(unit, other_skill))
            
class ImmuneChooseStatus(SkillComponent):
    nid = 'immune__choose_status'
    desc = "Unit does not receive negative statuses and is not affected by existing negative statuses"
    tag = SkillTags.STATUS
    
    expose = ComponentType.Skill
    value = ''

    def after_gain_skill(self, unit, other_skill):
        if other_skill.nid == self.value:
            if other_skill.negative and skill_system.condition(self.skill, unit):
                action.do(action.RemoveSkill(unit, other_skill))

class ImmunePropaganda(SkillComponent):
    nid = 'immune_propaganda'
    desc = "Better get out those MND boosters...?"
    tag = SkillTags.STATUS

    def after_gain_skill(self, unit, other_skill):
        if other_skill.nid == 'Mandate_of_Heaven' and unit.get_stat('MND') >= 10:
            action.do(action.RemoveSkill(unit, other_skill))
            
class PersonalSkill(SkillComponent):
    nid = 'learned_skill'
    desc = "Just for later."
    tag = SkillTags.ATTRIBUTE  
    
class CombatArtIndicator(SkillComponent):
    nid = 'combat_art_indicator'
    desc = "This skill should be displayed organizationally as a combat art."
    tag = SkillTags.ATTRIBUTE  
    
class AbilityIndicator(SkillComponent):
    nid = 'ability_indicator'
    desc = "This skill should be displayed organizationally as an ability."
    tag = SkillTags.ATTRIBUTE  
    
class PassengerSkill(SkillComponent):
    nid = 'passenger_skill'
    desc = "Actually matters mechanically."
    tag = SkillTags.ATTRIBUTE  
    
class EventAfterCombat(SkillComponent):
    nid = 'event_after_combat'
    desc = 'Calls event after any combat'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Event
    value = ''

    def end_combat(self, playback, unit: UnitObject, item, target: UnitObject, item2, mode):
        game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'mode': mode, 'item2': item2})
        
class EventAfterCombatWhenHit(SkillComponent):
    nid = 'event_after_combat_when_hit'
    desc = 'Calls event after any combat where unit is hit'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Event
    value = ''
    
    _got_hit = False
    
    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if strike == Strike.HIT or strike == Strike.CRIT:
            self._got_hit = True

    def end_combat(self, playback, unit: UnitObject, item, target: UnitObject, item2, mode):
        if self._got_hit and target:
            game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'mode': mode, 'item2': item2})
        self._got_hit = False
        
class EventWhenHit(SkillComponent):
    nid = 'event_when_hit'
    desc = 'Calls event when unit is hit'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Event
    value = ''
    
    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if strike == Strike.HIT or strike == Strike.CRIT:
            game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'mode': mode, 'item2': item2})
            
class EventOnUpkeep(SkillComponent):
    nid = 'event_on_upkeep'
    desc = "Triggers the designated event at upkeep"
    tag = SkillTags.TIME

    expose = ComponentType.Event
    value = ''
    
    def on_upkeep(self, actions, playback, unit):
        game.events.trigger_specific_event(self.value, unit, unit, unit.position, {'item': None, 'mode': None})
        
class CannotUseSpecificItem(SkillComponent):
    nid = 'cannot_use_specific_item'
    desc = "Unit cannot use or equip item with matching UID"
    tag = SkillTags.BASE
    
    expose = ComponentType.Int
    value = 1

    def available(self, unit, item) -> bool:
        return item.uid != self.value
        
class EventBeforeCombat(SkillComponent):
    nid = 'event_before_combat'
    desc = 'Calls event before any combat'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Event
    value = ''

    def start_combat(self, playback, unit: UnitObject, item, target: UnitObject, item2, mode):
        game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'item2': item2, 'mode': mode})
        
class TrueMiracleEvent(SkillComponent):
    nid = 'true_miracle_event'
    desc = "Unit cannot go beneath 1 HP. An event will occur once this effect triggers."
    tag = SkillTags.COMBAT2
    
    expose = ComponentType.Event
    value = ''

    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        did_something = False
        for act in reversed(actions):
            if isinstance(act, action.ChangeHP) and -act.num >= act.old_hp and act.unit == unit:
                act.num = -act.old_hp + 1
                did_something = True
                playback.append(pb.DefenseHitProc(unit, self.skill))

        if did_something:
            actions.append(action.TriggerCharge(unit, self.skill))
            game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'item2': item2, 'mode': mode})
            
class EventWhenDodging(SkillComponent):
    nid = 'event_when_dodging'
    desc = 'Calls event when unit dodges'
    tag = SkillTags.ADVANCED

    expose = ComponentType.Event
    value = ''
    
    def after_take_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if strike != Strike.HIT and strike != Strike.CRIT:
            game.events.trigger_specific_event(self.value, unit, target, unit.position, {'item': item, 'mode': mode, 'item2': item2})
            
class CannotUseSpecificItem(SkillComponent):
    nid = 'cannot_use_specific_item'
    desc = "Unit cannot use or equip item with matching UID"
    tag = SkillTags.BASE
    
    expose = ComponentType.Int
    value = 1

    def available(self, unit, item) -> bool:
        return item.uid != self.value
        
class MustUseReach(SkillComponent):
    nid = 'must_use_reach'
    desc = "Unit cannot equip non-reach items"
    tag = SkillTags.BASE

    def available(self, unit, item) -> bool:
        return not item_system.equippable(unit, item) or 'Reach' in item.tags or item_system.is_accessory(unit, item)
        
class GiveStatusAfterStrike(SkillComponent):
    nid = 'give_status_after_strike'
    desc = "Gives a status to target after any strike attempt"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Skill

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        if target:
            actions.append(action.AddSkill(target, self.value, unit))
            actions.append(action.TriggerCharge(unit, self.skill))
            
class ExpressionGrowthChange(SkillComponent):
    nid = 'expression_growth_change'
    desc = "aaaaagh"
    tag = SkillTags.COMBAT

    expose = (ComponentType.StringDict, ComponentType.Stat)
    value = []

    def growth_change(self, unit=None):
        from app.engine import evaluate
        try:
            return {stat[0]: int(evaluate.evaluate(stat[1], unit)) for stat in self.value}
        except Exception as e:
            logging.error("Couldn't evaluate conditional for skill %s: [%s], %s", self.skill.nid, str(self.value), e)
        return {stat[0]: 0 for stat in self.value}

class BuildChargeStartCharged(SkillComponent):
    nid = 'build_charge_start_charged'
    desc = "Skill starts each chapter with full charges. Skill will only be active while the there are *value* or more charges. Upon use of skill, charges are reset to 0. Often used with Combat Arts."
    tag = SkillTags.CHARGE

    expose = ComponentType.Int
    value = 10

    ignore_conditional = True

    def init(self, skill):
        self.skill.data['charge'] = self.value
        self.skill.data['total_charge'] = self.value

    def condition(self, unit, item):
        return self.skill.data['charge'] >= self.skill.data['total_charge']

    def on_end_chapter(self, unit, skill):
        self.skill.data['charge'] = self.skill.data['total_charge']

    def trigger_charge(self, unit, skill):
        action.do(action.SetObjData(self.skill, 'charge', 0))

    def text(self) -> str:
        return str(self.skill.data['charge'])

    def cooldown(self):
        if self.skill.data.get('total_charge'):
            return self.skill.data['charge'] / self.skill.data['total_charge']
        else:
            return 1
            
class DeathRecoil(SkillComponent):
    nid = 'deathrecoil'
    desc = "Unit takes lethal damage after combat with an enemy"
    tag = SkillTags.COMBAT2

    expose = ComponentType.Int
    value = 0
    author = 'Lord_Tweed'

    def end_combat(self, playback, unit, item, target, item2, mode):
        if target and skill_system.check_enemy(unit, target):
            action.do(action.TriggerCharge(unit, self.skill))
            end_health = unit.get_hp() - self.value
            action.do(action.SetHP(unit, max(0, end_health)))
            if end_health <= 0:
                game.death.should_die(unit)
                game.state.change('dying')
                game.events.trigger(triggers.UnitDeath(unit, None, unit.position))
                skill_system.on_death(unit)

class CiggieRecoil(SkillComponent):
    nid = 'mid_battle_recoil'
    desc = "Use negative number for mid-battle recoil (can be lethal)"
    tag = SkillTags.COMBAT2

    expose = ComponentType.String
    value = 1

    def after_strike(self, actions, playback, unit, item, target, item2, mode, attack_info, strike):
        from app.engine import evaluate
        try:
            local_args = {'item': item, 'item2': item2, 'mode': mode, 'skill': self.skill, 'attack_info': attack_info}
            calc_value = int(evaluate.evaluate(self.value, unit, target, unit.position, local_args))
            actions.append(action.ChangeHP(unit, calc_value))
            playback.append(pb.DamageHit(unit, item, unit, calc_value, calc_value))
            playback.append(pb.UnitTintAdd(unit, (255, 0, 0)))
            playback.append(pb.HitSound('FireHit'))
            if calc_value > 0:
                playback.append(pb.HitSound('Attack Hit ' + str(random.randint(1, 5))))
            else:
                playback.append(pb.HitSound('Final Hit'))
            actions.append(action.TriggerCharge(unit, self.skill))
        except Exception as e:
            logging.error("Couldn't evaluate %s conditional (%s)", self.value, e)
            return 0
