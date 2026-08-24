from packaging.version import Version
from app_config import *
import os

class Database():
    def __init__(self, host="localhost", database="database", user="admin", password="admin"):
        self.host = host
        self.database = database
        self.user = user
        self.password = password

    def connect():
        return False
    
    def disconnect():
        return False
    
    def read_board_info(model:str):
        return None

    def read_im_recipe(self, serial_number: str):
        return None

    def read_sb_recipe(self, serial_number: str):
        return None
    
import json
# import mysql.connector
class MySQLDatabase(Database):

    def __init__(self, host="localhost", database="database", user="admin", password="admin"):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
    
    def connect(self):
        return True
    
    def disconnect(self):
        return True
    
    def read_board_info(self, model:str):
        try:
            pass
        except:
            return []
        return []
    
    def read_all_board_info(self):
        try:
            pass
        except:
            return []
        return []

import pyodbc
class MicrosoftSQLDatabase(Database):

    def __init__(self, host="localhost", database="database", user="admin", password="admin", table="vwDataExport_SerialNumbers_Line", driver='"SQL Server" '):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self.driver = driver
        self.table = table
    
    def connect(self):
        if self.conn != None:
            self.disconnect()
        try:
            connection_string = f'DRIVER={self.driver};SERVER={self.host};DATABASE={self.database};UID={self.user};PWD={self.password}'
            
            self.conn = pyodbc.connect(connection_string)
            self.cursor = self.conn.cursor()
  
        except Exception as e:
            print(e)
            return False
        return True
    
    def disconnect(self):
        if self.conn != None:
            self.conn.close()
            self.conn = None
        return True
    
    def read_board_info(self, model:str):
        row = None
        try:
            # query = f"SELECT SerialNumber, Article FROM {self.table} WHERE SerialNumber = ?"
            query = f"""
SELECT TRIM(f.SerialNumber) AS SerialNumber,
       TRIM(a.CodeGroup) AS Article
FROM
     HITECO_MDS.dbo.Live_MasterCycle AS m
      JOIN HITECO_MDS.dbo.Live_MasterCycleFakeSerialNumber AS f ON f.IdMasterCycle = m.IdMasterCycle
      JOIN HITECO_MDS.dbo.GroupMasterCycle AS g ON g.IdMasterCycle = m.IdMasterCycle
      JOIN HITECO_MDS.dbo.AnaPmgGroup AS a ON a.IdGroup = g.IdGroup
      JOIN HITECO_MDS.dbo.OrderPlan AS o ON o.IdOrderPlan = m.IdOrderPlan
      JOIN HITECO_MDS.dbo.OrderState AS s ON o.OrderState = s.IdOrderState
      JOIN HITECO_MDS.dbo.AnaLine AS l ON l.IdLine = o.IdLine
WHERE  l.CodeLine = 'LN1'
       AND TRIM(f.SerialNumber) = TRIM(?);"""
            self.cursor.execute(query, (model,))

            rows = self.cursor.fetchall()
            if len(rows):
                row = rows[0]
                print(f"Serial: {row.SerialNumber}, Articolo: {row.Article}")                  
            # 4. Esecuzione (Passa i parametri come tupla)
        except:
            return None
        if row != None:
            # Estraggo ricetta
            try:
                recipe_path = os.path.join(CONFIG_RECIPE_BASE_PATH, row.Article, "recipe.json")
                with open(recipe_path) as f:
                    d = json.load(f)
                    d["model"] = row.Article
                    d["serial"] = row.SerialNumber
            except Exception as e:
                raise RuntimeError(f"Ricetta per {row.Article} non trovata nel database - {e}")
            return d
        else:
            raise RuntimeError( "Matricola non trovata nel database" )

    def read_test_board_info(self, model:str):
        row = None
        try:
            query = """
SELECT Recipe
FROM HITECO_MDS_SER.dbo.vwDataExport_SerialNumberArticleRecipe
WHERE RecipeType = 'IM'
  AND TRIM(SerialNumber) = TRIM(?);"""
            self.cursor.execute(query, (model,))

            rows = self.cursor.fetchall()
            if len(rows):
                row = rows[0]
                print(f"Recipe: {row.Recipe}")
        except:
            return None
        if row != None:
            return row.Recipe
        else:
            raise RuntimeError("Matricola non trovata nel database")

    def read_sb_recipe(self, serial_number: str):
        row = None
        try:
            query = f"""
SELECT Recipe
FROM {self.database}.dbo.vwDataExport_SerialNumberArticleRecipe
WHERE SerialNumber = ?
  AND RecipeType = 'SB';"""
            self.cursor.execute(query, (serial_number,))

            rows = self.cursor.fetchall()
            if len(rows):
                row = rows[0]
                print(f"SB Recipe: {row[0]}")
        except Exception as e:
            raise RuntimeError(f"Errore durante la lettura della ricetta SB - {e}")
        if row is not None:
            return row[0]
        else:
            raise RuntimeError("Matricola non trovata nel database")

    def read_im_recipe(self, serial_number: str):
        row = None
        try:
            query = f"""
SELECT Recipe
FROM {self.database}.dbo.vwDataExport_SerialNumberArticleRecipe
WHERE SerialNumber = ?
  AND RecipeType = 'IM';"""
            self.cursor.execute(query, (serial_number,))

            rows = self.cursor.fetchall()
            if len(rows):
                row = rows[0]
                print(f"IM Recipe: {row[0]}")
        except Exception as e:
            raise RuntimeError(f"Errore durante la lettura della ricetta SB - {e}")
        if row is not None:
            return row[0]
        else:
            raise RuntimeError("Matricola non trovata nel database")


    def read_all_board_info(self):
        try:
            query = f"SELECT SerialNumber, Article FROM {self.table}"
            self.cursor.execute(query)

            rows = self.cursor.fetchall()
            
            if rows:
                for row in rows:
                    # In pyodbc puoi accedere per indice o nome
                    print(f"Serial: {row.SerialNumber}, Articolo: {row.Article}")
            # 4. Esecuzione (Passa i parametri come tupla)
        except:
            return None
        return rows
    
    def read_all_test_recipe(self):
        try:
            query = f"SELECT SerialNumber, Article FROM {self.table}"
            self.cursor.execute(query)

            rows = self.cursor.fetchall()
            
            if rows:
                for row in rows:
                    # In pyodbc puoi accedere per indice o nome
                    print(f"Serial: {row.SerialNumber}, Articolo: {row.Article}")
            # 4. Esecuzione (Passa i parametri come tupla)
        except:
            return None
        return rows

class FakeDatabase(Database):

    def connect(self):
        return True
    
    def disconnect(self):
        return True
    
    def read_board_info(self, model:str):
        info = {}
        with open('fakerecipe.json') as f:
            d = json.load(f)
        info["recipe"] = d
        info["fw_version"] = {}
        info["fw_version"]["code"] = Version("3.4")
        info["fw_version"]["path"] = "assets/firmware/im_3.3.bin"
        return info

class MecalDatabase(Database):

    def connect(self):
        return True
    
    def disconnect(self):
        return True
    
    def read_board_info(self, model:str):
        d = {}
        with open('mecal_recipe.json') as f:
            d = json.load(f)

        return d
class TestDatabase(Database):

    def connect(self):
        return True
    
    def disconnect(self):
        return True
    
    def read_board_info(self, model:str):
        d = {}
        with open('test_recipe.json') as f:
            d = json.load(f)

        return d

import time
import sys
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sb"

    if mode == "sb":
        #db = MicrosoftSQLDatabase("I40PRDHIDBWIN", "HITECO_MDS_SER", "MesReader", "reader", driver="SQL Server")
        db = MicrosoftSQLDatabase("I40TSTHIDBWIN", "HITECO_MDS_SER", "MesReader", "reader", driver="SQL Server")
        if not db.connect():
            print("Connessione al database fallita")
            exit(1)

        test_serials = [
            "H24J002819",
        ]

        print("=== Test read_sb_recipe ===")
        for sn in test_serials:
            try:
                start = time.perf_counter()
                recipe = db.read_sb_recipe(sn)
                elapsed = time.perf_counter() - start
                print(f"[OK] {sn} -> Recipe: {recipe}  ({elapsed:.4f}s)")
            except Exception as e:
                print(f"[FAIL] {sn} -> {e}")

    elif mode == "board":
        db = MicrosoftSQLDatabase("I40PRDHIDBWIN", "HITECO_MDS", "Mes_Reader", "reader", driver="SQL Server")
        if not db.connect():
            print("Connessione al database fallita")
            exit(1)

        test_serials = [
            "H24J002819",
        ]

        print("=== Test read_board_info ===")
        for sn in test_serials:
            try:
                start = time.perf_counter()
                info = db.read_board_info(sn)
                elapsed = time.perf_counter() - start
                print(f"[OK] {sn} -> {info}  ({elapsed:.4f}s)")
            except Exception as e:
                print(f"[FAIL] {sn} -> {e}")

    else:
        print(f"Modalità '{mode}' non riconosciuta. Usa: sb | board")

    db.disconnect()
