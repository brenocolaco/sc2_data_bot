from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.player import Bot, Computer
from sc2.ids.unit_typeid import UnitTypeId

class WorkerBot(BotAI):
    async def on_step(self, iteration):
        # 1. Distribuir trabalhadores nos minerais automaticamente
        await self.distribute_workers()

        # 2. Verificamos se ainda temos uma base (Nexus)
        if not self.townhalls.ready:
            # Se não houver Nexus pronto, o bot não faz nada (espera o defeat)
            return

        # Agora sabemos que pelo menos um nexus existe
        nexus = self.townhalls.ready.random

        # 3. Treinar trabalhadores
        if self.can_afford(UnitTypeId.PROBE) and nexus.is_idle:
            nexus.train(UnitTypeId.PROBE)

        # 4. Construir Pylons (usando o nexus que agora é garantido)
        if self.supply_left < 3 and not self.already_pending(UnitTypeId.PYLON):
            if self.can_afford(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=nexus)

# Rodar o jogo
if __name__ == "__main__":
    run_game(maps.get("AutomatonLE"), [
        Bot(Race.Protoss, WorkerBot()),
        Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)