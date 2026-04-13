#Imports para o bot

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.player import Bot, Computer
from sc2.ids.unit_typeid import UnitTypeId

# Imports para o banco de dados

import sqlite3
import os
from sc2.data import Result

#Definimos a classe do bot
class WorkerBot(BotAI):
    # O __init__ permite que o bot 'saiba' a dificuldade assim que nasce
    def __init__(self, difficulty_level="Unknown"):
        super().__init__()
        self.difficulty_level = difficulty_level

    async def on_step(self, iteration):
        """
        on_step roda a cada 'frame' do jogo. É o loop de varredura (como num CLP).
        O parâmetro 'iteration' conta quantos passos já foram dados.

        """
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
        
        # 5. COLETA DE GÁS (Assimilators)
        # Construímos gás se tivermos um Gateway ou se estivermos com muito mineral
        if self.can_afford(UnitTypeId.ASSIMILATOR) and self.structures(UnitTypeId.GATEWAY).exists:
            for geyser in self.vespene_geyser.closer_than(15, nexus):
                if not self.structures(UnitTypeId.ASSIMILATOR).closer_than(2, geyser).exists:
                    await self.build(UnitTypeId.ASSIMILATOR, near=geyser)

        # 6. PRODUÇÃO MILITAR ESCALÁVEL
        # Definimos um limite (ex: 3 Gateways). 
        # .amount conta quantos você tem (prontos ou em construção)
        if self.structures(UnitTypeId.GATEWAY).amount < 3:
            if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                # Sempre usamos o nexus mais próximo para construir perto
                await self.build(UnitTypeId.GATEWAY, near=nexus)
        
        # Treinar Zealots se o Gateway estiver parado
        for gw in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if self.can_afford(UnitTypeId.ZEALOT) and self.supply_left > 2:
                gw.train(UnitTypeId.ZEALOT)

        # 7. EXPANSÃO (Novo Nexus)
        # Se a base atual estiver quase saturada (ex: 14+ trabalhadores) e tivermos 400 minerais
        if not self.already_pending(UnitTypeId.NEXUS):
        # Expande se tivermos muitos trabalhadores ou muito dinheiro sobrando
        # 16 minerais + 6 gás = 22 é a saturação ideal por base
            if self.supply_workers > (self.townhalls.amount * 20) or self.minerals > 1000:
                if self.can_afford(UnitTypeId.NEXUS):
                    await self.expand_now()
        
        # 8. LÓGICA DE ATAQUE (O Ponto de Rutura)
        # Filtramos apenas os Zealots que estão prontos
        zealots = self.units(UnitTypeId.ZEALOT).ready

        # Se tivermos 15 ou mais, mandamos o ataque total
        if zealots.amount >= 15:
            # Localização da base inimiga principal
            target = self.enemy_start_locations[0]
            
            for zealot in zealots:
                # Comandamos cada unidade a atacar o alvo
                zealot.attack(target)

        # OPCIONAL: Se tivermos poucos Zealots, podemos mandá-los defender o Nexus
        elif zealots.amount > 0:
            for zealot in zealots.idle:
                # Ficam em guarda perto do Nexus principal
                zealot.attack(nexus.position)

    async def on_end(self, game_result):
        """
        Método executado automaticamente ao fim da partida.
        Aqui é onde vamos pegar os dados para colocar no banco de dados.

        """
        print(f"Fim de jogo: {game_result}")

        # 1. Preparar os dados
        resultado = "Vitoria" if game_result == Result.Victory else "Derrota"
        duracao = self.time  # Tempo em segundos
        # Métrica simples de economia: Minerais atuais + Minerais gastos
        minerais_totais = self.state.score.collected_minerals 
        trabalhadores = self.supply_workers

        # BLOCO DE CONEXÃO SQL (Try/Except para evitar que o script trave se o banco sumir)
        # 2. Conectar e salvar no banco
        try:
            db_path = os.path.join("data", "sc2_results.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # AGORA O INSERT TEM 5 CAMPOS (adicionamos a dificuldade no fim)
            cursor.execute('''
                INSERT INTO matches (result, duration_s, minerals_collected, workers_built, difficulty)
                VALUES (?, ?, ?, ?, ?)
            ''', (resultado, self.time, self.state.score.collected_minerals, self.supply_workers, self.difficulty_level))

            conn.commit()
            conn.close()
            print(f"Dados salvos! Dificuldade registrada: {self.difficulty_level}")
        except Exception as e:
            print(f"Erro ao salvar: {e}")
            
# Rodar o jogo
if __name__ == "__main__":
    # Escolha a dificuldade aqui
    nivel_dificuldade = Difficulty.Hard 

    run_game(maps.get("AutomatonLE"), [
        # Aqui passamos o nome da dificuldade (ex: "Hard") para o bot guardar
        Bot(Race.Protoss, WorkerBot(difficulty_level=nivel_dificuldade.name)),
        Computer(Race.Terran, nivel_dificuldade)
    ], realtime=True)