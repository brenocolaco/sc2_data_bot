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

# Imports para os mapas

import random
from pathlib import Path

#Import para o finally
import time

#Definimos a classe do bot
class WorkerBot(BotAI):
    # O __init__ permite que o bot 'saiba' a dificuldade assim que nasce
    def __init__(self, difficulty_level="Unknown", map_name="Unknown"):
        super().__init__()
        self.difficulty_level = difficulty_level
        self.map_name = map_name
        self.resultado_final = "Interrompido" # Valor padrão para quando o jogo for fechado

        # Variáveis de backup para o BI
        self.minerais_backup = 0
        self.tempo_backup = 0
        self.workers_backup = 0

    async def on_step(self, iteration):
        """
        on_step roda a cada 'frame' do jogo. É o loop de varredura (como num CLP).
        O parâmetro 'iteration' conta quantos passos já foram dados.

        """
        # Atualiza os backups a cada frame
        self.minerais_backup = self.state.score.collected_minerals
        self.tempo_backup = self.time
        self.workers_backup = self.supply_workers

        # 1. Distribuir trabalhadores nos minerais automaticamente
        await self.distribute_workers()

        # 2. Verificamos se ainda temos uma base (Nexus)
        if not self.townhalls.ready:
            # Se não houver Nexus pronto, o bot não faz nada (espera o defeat)
            return

        # Agora sabemos que pelo menos um nexus existe
        nexus = self.townhalls.ready.random

        #Posicionamento
        posicao = nexus.position.towards(self.game_info.map_center, 8)

        # 3. Treinar trabalhadores
        if self.can_afford(UnitTypeId.PROBE) and nexus.is_idle:
            nexus.train(UnitTypeId.PROBE)

        # 4. Construir Pylons (usando o nexus que agora é garantido)
        if self.supply_left < 3 and not self.already_pending(UnitTypeId.PYLON):
            if self.can_afford(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=posicao)
        
        # 5. COLETA DE GÁS (Assimilators)
        # Construímos gás se tivermos um Gateway ou se estivermos com muito mineral
        if self.can_afford(UnitTypeId.ASSIMILATOR) and not self.structures(UnitTypeId.GATEWAY).exists:
            for geyser in self.vespene_geyser.closer_than(15, nexus):
                await self.build(UnitTypeId.ASSIMILATOR, near=geyser)

        # 6. PRODUÇÃO MILITAR ESCALÁVEL
        # Definimos um limite (ex: 3 Gateways). 
        # .amount conta quantos você tem (prontos ou em construção)
        if self.structures(UnitTypeId.GATEWAY).amount < 3:
            if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                # Sempre usamos o nexus mais próximo para construir perto
                await self.build(UnitTypeId.GATEWAY, near=posicao)
        
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
            if self.enemy_structures.exists:
                target = self.enemy_structures.random.position
            else:
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
        
        """

        # Lógica de decisão do status
        if game_result == Result.Victory:
            self.resultado_final = "Vitoria"
        elif game_result == Result.Defeat:
            self.resultado_final = "Derrota"

        print(f"Evento on_end disparado! Resultado: {self.resultado_final}")

                    
# Rodar o jogo
def get_random_map():
    # Caminho padrão onde o SC2 instala os mapas
    # Se você tiver uma pasta específica, mude o caminho abaixo
    map_path = Path("C:/Program Files (x86)/StarCraft II/Maps")
    
    # Lista todos os arquivos .SC2Map recursivamente
    all_maps = list(map_path.glob("**/*.SC2Map"))
    
    if not all_maps:
        return "AutomatonLE" # Fallback caso não encontre nada
    
    # Retorna apenas o nome do mapa (sem a extensão .SC2Map)
    return random.choice(all_maps).stem

if __name__ == "__main__":
    nivel = Difficulty.VeryHard
    mapa_escolhido = get_random_map()

    # Criamos a instância do bot fora do run_game para acessar os dados depois
    meu_bot = WorkerBot(difficulty_level=nivel.name, map_name=mapa_escolhido)

    print(f"Iniciando partida no mapa: {mapa_escolhido}")

    try:
        run_game(maps.get(mapa_escolhido), [
            Bot(Race.Protoss, meu_bot),
            Computer(Race.Terran, nivel)
        ], realtime=False)
    except Exception as e:
        # Isso evita que aquele "mar de vermelho" apareça no seu terminal
        print(f"Partida encerrada pelo usuário ou erro de conexão: {e}")
    finally:
        time.sleep(2)

        print(f"Iniciando salvamento... Status atual: {meu_bot.resultado_final}")
        
        try:
            db_path = os.path.join("data", "sc2_results.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Capturamos os dados que o bot conseguiu minerar até o momento do fechamento
            cursor.execute('''
                INSERT INTO matches (result, duration_s, minerals_collected, workers_built, difficulty, map_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                meu_bot.resultado_final, 
                meu_bot.tempo_backup, 
                meu_bot.minerais_backup, 
                meu_bot.workers_backup, 
                meu_bot.difficulty_level, 
                meu_bot.map_name
            ))

            conn.commit()
            conn.close()
            print(f"Partida registrada como: {meu_bot.resultado_final}")
        except Exception as db_error:
            print(f"Erro ao salvar no banco: {db_error}")