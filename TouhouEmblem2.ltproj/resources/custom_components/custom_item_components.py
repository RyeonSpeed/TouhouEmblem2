from __future__ import annotations

from app.data.database.components import ComponentType
from app.data.database.database import DB
from app.data.database.item_components import ItemComponent, ItemTags
from app.engine import (action, banner, combat_calcs, engine, equations,
                        image_mods, item_funcs, item_system, skill_system)
from app.engine.game_state import game
from app.engine.objects.unit import UnitObject
from app.utilities import utils, static_random


class DoNothing(ItemComponent):
    nid = 'do_nothing'
    desc = 'does nothing'
    tag = ItemTags.CUSTOM

    expose = ComponentType.Int
    value = 1

class KindaMagic(ItemComponent):
    nid = 'kinda_magic'
    desc = 'Makes Item use magic damage formula but not magic anims'
    tag = ItemTags.WEAPON

    def damage_formula(self, unit, item):
        return 'MAGIC_DAMAGE'

    def resist_formula(self, unit, item):
        return 'MAGIC_DEFENSE'

class AllyBlastAOEExceptUnit(ItemComponent):
    nid = 'ally_blast_aoe_except_unit'
    desc = "Gives Blast AOE that only hits allies except self"
    tag = ItemTags.AOE
    
    expose = ComponentType.Equation  # Radius
    value = None
    
    def splash(self, unit, item, position) -> tuple:
        ranges = set(range(self._get_power(unit)))
        splash = game.target_system.find_manhattan_spheres(ranges, position[0], position[1])
        splash = {pos for pos in splash if game.tilemap.check_bounds(pos)}
        from app.engine import skill_system
        splash = [game.board.get_unit(s) for s in splash]
        splash = [s.position for s in splash if s and skill_system.check_ally(unit, s) and s is not unit]
        return None, splash

    def _get_power(self, unit) -> int:
        from app.engine import equations
        value = equations.parser.get(self.value, unit)
        empowered_splash = skill_system.empower_splash(unit)
        return value + 1 + empowered_splash
        
class PropertyChangeExpression(ItemComponent):
    nid = 'property_change_expression'
    desc = "Adds amount to an item's component's value. Do not use unless you know what you're doing."
    tag = ItemTags.WEAPON
    
    expose = ComponentType.NewMultipleOptions

    options = {
        'weapon_property': ComponentType.String,
        'modify_expression': ComponentType.String,
    }
    
    def __init__(self, value=None):
        self.value = {
            'weapon_property': "damage",
            'modify_expression': "0",
        }
        if value:
            self.value.update(value)
            
    def init(self, item):
        item.data['target_item'] = None

    def _target_restrict(self, defender):
        # Unit has item that can be buffed
        for item in defender.items:
            if self.item_restrict(None, None, defender, item):
                return True
        return False

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        # Unit has item that can be buffed
        defender = game.board.get_unit(def_pos)
        if not defender:
            return False
        return self._target_restrict(defender)

    def simple_target_restrict(self, unit, item):
        return self._target_restrict(unit)

    def targets_items(self, unit, item) -> bool:
        return True

    def item_restrict(self, unit, item, defender, def_item) -> bool:
        from app.engine import evaluate
        if def_item.weapon:
            return True
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        target_item = item.data.get('target_item')
        if target_item:
            from app.engine import evaluate
            try:
                action.do(action.ModifyItemComponent(target_item, self.value['weapon_property'], int(evaluate.evaluate(self.value['modify_expression'], target)), None, True))
            except Exception as e:
                print("Fuck you.")
            

    def end_combat(self, playback, unit, item, target, item2, mode):
        item.data['target_item'] = None