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