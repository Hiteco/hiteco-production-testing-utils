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
            logging.error(f"Errore connessione database: {e}")
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
                logging.info(f"Serial: {row.SerialNumber}, Articolo: {row.Article}")                  
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
    
    def read_all_board_info(self):
        try:
            query = f"SELECT SerialNumber, Article FROM {self.table}"
            self.cursor.execute(query)

            rows = self.cursor.fetchall()
            
            if rows:
                for row in rows:
                    # In pyodbc puoi accedere per indice o nome
                    logging.info(f"Serial: {row.SerialNumber}, Articolo: {row.Article}")
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
if __name__ == "__main__":
    for driver in pyodbc.drivers():
        print(driver)
    db = MicrosoftSQLDatabase( "I40PRDHIDBWIN", "HITECO_MDS", "Mes_Reader", "reader", driver="SQL Server" )
    db.connect()
    ids = [
        "H25H002267",
        "H26A002530",
        "H26A002532",
        "H26A002533",
        "H26A002534",
        "H26C000976",
    ]
    for id in ids:
        # print( db.read_all_board_info() )
        try:
            start_time = time.perf_counter()
            db.read_board_info( id )
            end_time = time.perf_counter()
            durata = end_time - start_time
            print(f"La query ha impiegato {durata:.4f} secondi")
        except Exception as e:
            print( f"Errore durante la lettura della matricola {id}, {str(e)}" )
    db.disconnect()
