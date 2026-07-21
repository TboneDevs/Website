import asyncio
import aiohttp
import json
import os
import re
import sqlite3
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("CPM-Nuker")

# === CPM Server Constants (Required) ===
FK = "AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM"
SU = "https://europe-west1-cp-multiplayer.cloudfunctions.net/SavePlayerRecordsIOS1"
LU = "https://europe-west1-cp-multiplayer.cloudfunctions.net/GetPlayerRecordsIOS1"
RU = "https://us-central1-cp-multiplayer.cloudfunctions.net/SetUserRating4"
MAX_MONEY = 50_000_000
MAX_COIN  = 500_000


class CPMNuker:
    def __init__(self):
        self.db_path = "cpm_tokens.db"
        self.user_data_cache: Dict[str, Dict] = {}
        self.base_headers = {
            "User-Agent": "okhttp/3.12.13",
            "Content-Type": "application/json",
        }
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    user_id          INTEGER PRIMARY KEY,
                    auth_token       TEXT,
                    email            TEXT,
                    password         TEXT,
                    refresh_token    TEXT,
                    token_expires_at REAL,
                    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    cache_key  TEXT PRIMARY KEY,
                    email      TEXT,
                    data_json  TEXT,
                    saved_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER,
                    label      TEXT,
                    data_json  TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.commit()

    def _cache_key(self, uid: int, email: str = None) -> str:
        if email:
            return f"{uid}_{email}"
        td = self.get_token_data(uid)
        if td and td.get("email"):
            return f"{uid}_{td['email']}"
        return str(uid)

    # ── Token management ──────────────────────────────────────
    def save_token(self, uid: int, auth: str, email: str, pw: str = None, rt: str = None):
        exp = time.time() + 3600
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                INSERT OR REPLACE INTO tokens
                (user_id, auth_token, email, password, refresh_token, token_expires_at)
                VALUES (?,?,?,?,?,?)
            """, (uid, auth, email, pw, rt, exp))
            c.commit()

    def get_token_data(self, uid: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("""
                SELECT auth_token, email, password, refresh_token, token_expires_at
                FROM tokens WHERE user_id = ?
            """, (uid,)).fetchone()
        if row:
            return {
                "auth_token": row[0], "email": row[1],
                "password": row[2], "refresh_token": row[3],
                "token_expires_at": row[4]
            }
        return None

    def get_token(self, uid: int) -> Optional[Dict]:
        td = self.get_token_data(uid)
        if td:
            return {"auth_token": td["auth_token"], "email": td["email"]}
        return None

    def get_auth_token(self, uid: int) -> Optional[str]:
        td = self.get_token_data(uid)
        return td["auth_token"] if td else None

    def update_token(self, uid: int, auth: str, rt: str = None):
        exp = time.time() + 3600
        with sqlite3.connect(self.db_path) as c:
            if rt:
                c.execute("""
                    UPDATE tokens SET auth_token=?, refresh_token=?, token_expires_at=?
                    WHERE user_id=?
                """, (auth, rt, exp, uid))
            else:
                c.execute("""
                    UPDATE tokens SET auth_token=?, token_expires_at=?
                    WHERE user_id=?
                """, (auth, exp, uid))
            c.commit()

    def delete_token(self, uid: int):
        with sqlite3.connect(self.db_path) as c:
            c.execute("DELETE FROM tokens WHERE user_id=?", (uid,))
            c.commit()
        for k in [k for k in self.user_data_cache if k.startswith(str(uid))]:
            del self.user_data_cache[k]

    def is_token_expired(self, uid: int) -> bool:
        td = self.get_token_data(uid)
        if not td or not td.get("token_expires_at"):
            return True
        return td["token_expires_at"] < time.time()

    # ── User data ──────────────────────────────────────────────
    def get_user_template(self, uid: int, email: str = None) -> Dict:
        ck = self._cache_key(uid, email)
        if ck not in self.user_data_cache:
            saved = self._load_user_data(ck)
            if saved:
                self.user_data_cache[ck] = saved
            else:
                # Empty safe template — no zeros that overwrite real data
                self.user_data_cache[ck] = {
                    "Name": "",
                    "localID": "",
                    "money": 0,
                    "coin": 0,
                    "floats": [],
                    "integers": [],
                    "wheels": [],
                    "animations": [],
                    "personEquipmentsMale": {},
                    "personEquipmentsFemale": {},
                    "carIDnStatus": {},
                    "LevelsDoneTime": []
                }
        return self.user_data_cache[ck]

    def save_user_template(self, uid: int, data: Dict, email: str = None):
        ck = self._cache_key(uid, email)
        self.user_data_cache[ck] = data
        self._save_user_data(ck, email, data)

    def _save_user_data(self, ck: str, email: str, data: Dict):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                INSERT OR REPLACE INTO user_data (cache_key, email, data_json)
                VALUES (?,?,?)
            """, (ck, email, json.dumps(data)))
            c.commit()

    def _load_user_data(self, ck: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("""
                SELECT data_json FROM user_data WHERE cache_key=?
            """, (ck,)).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                pass
        return None

    def save_backup(self, uid: int, label: str, data: Dict):
        with sqlite3.connect(self.db_path) as c:
            c.execute(
                "INSERT INTO backups (user_id,label,data_json) VALUES (?,?,?)",
                (uid, label, json.dumps(data))
            )
            c.commit()

    def get_backups(self, uid: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as c:
            rows = c.execute(
                "SELECT id,label,created_at FROM backups WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
                (uid,)
            ).fetchall()
        return [{"id": r[0], "label": r[1], "time": r[2]} for r in rows]

    def restore_backup(self, uid: int, backup_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as c:
            row = c.execute(
                "SELECT data_json FROM backups WHERE id=? AND user_id=?",
                (backup_id, uid)
            ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                pass
        return None

    # ── HTTP ──────────────────────────────────────────────────
    async def _request(self, url: str, payload: Dict = None,
                       headers: Dict = None, params: Dict = None) -> Optional[Dict]:
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(ssl=False)
            h = {**self.base_headers, **(headers or {})}
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as s:
                async with s.post(url, json=payload or {}, headers=h, params=params or {}) as r:
                    text = await r.text()
                    try:
                        return json.loads(text)
                    except Exception:
                        return {"raw": text}
        except Exception as e:
            log.error(f"HTTP error: {e}")
            return None

    # ── Token refresh ─────────────────────────────────────────
    async def _refresh_token(self, uid: int) -> Tuple[bool, str]:
        td = self.get_token_data(uid)
        if not td:
            return False, "NO_TOKEN"
        rt = td.get("refresh_token")
        em = td.get("email")
        pw = td.get("password")

        if rt:
            r = await self._request(
                f"https://securetoken.googleapis.com/v1/token?key={FK}",
                {"grant_type": "refresh_token", "refresh_token": rt}
            )
            if r and r.get("id_token"):
                self.update_token(uid, r["id_token"], r.get("refresh_token", rt))
                return True, "OK"

        if em and pw:
            res = await self.account_login(em, pw)
            if res.get("ok"):
                self.update_token(uid, res["auth"], res.get("refresh_token", ""))
                return True, "OK"

        return False, "REFRESH_FAILED"

    async def get_valid_token(self, uid: int) -> Tuple[bool, str, str]:
        if self.is_token_expired(uid):
            ok, msg = await self._refresh_token(uid)
            if not ok:
                return False, msg, ""
        td = self.get_token_data(uid)
        if td and td.get("auth_token"):
            return True, "OK", td["auth_token"]
        return False, "NO_TOKEN", ""

    # ── Login ─────────────────────────────────────────────────
    async def account_login(self, email: str, password: str) -> Dict[str, Any]:
        url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={FK}"
        r = await self._request(url, {
            "email": email, "password": password,
            "returnSecureToken": True,
            "clientType": "CLIENT_TYPE_ANDROID"
        }, headers={
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; SM-A025F Build/SP1A.210812.016)"
        })

        if not r:
            return {"ok": False, "message": "NETWORK_ERROR"}
        if "idToken" in r:
            return {
                "ok": True, "message": "OK",
                "auth": r["idToken"],
                "refresh_token": r.get("refreshToken", "")
            }
        err = r.get("error", {}).get("message", "").upper()
        for key in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "TOO_MANY_ATTEMPTS",
                    "USER_DISABLED", "INVALID_EMAIL", "INVALID_LOGIN_CREDENTIALS"]:
            if key in err:
                return {"ok": False, "message": key}
        return {"ok": False, "message": "LOGIN_FAILED"}

    # ── LOAD REAL ACCOUNT DATA FROM SERVER ────────────────────
    async def load_account(self, uid: int, force: bool = False) -> bool:
        """
        Fetch real player data from CPM servers.
        Returns True if successful, False if failed.
        CRITICAL: Must be called before any modification.
        """
        ck = self._cache_key(uid)

        # If already cached and not forced, skip loading
        if not force and ck in self.user_data_cache:
            saved = self._load_user_data(ck)
            if saved:
                return True

        ok, msg, auth = await self.get_valid_token(uid)
        if not ok:
            log.warning(f"load_account: No valid token for {uid}: {msg}")
            return False

        try:
            r = await self._request(
                LU,
                {"data": json.dumps({})},
                {"Authorization": f"Bearer {auth}"}
            )

            if not r:
                log.warning(f"load_account: No response for {uid}")
                return False

            # Try to parse the result
            real_data = None

            # Case 1: result is a JSON string
            if "result" in r:
                try:
                    real_data = json.loads(r["result"])
                except Exception:
                    real_data = r["result"]

            # Case 2: data key
            elif "data" in r:
                try:
                    real_data = json.loads(r["data"])
                except Exception:
                    real_data = r["data"]

            # Case 3: response itself is the data
            elif isinstance(r, dict) and "Name" in r:
                real_data = r

            if real_data and isinstance(real_data, dict):
                # Validate it has real game fields
                has_game_data = any(
                    k in real_data for k in
                    ["Name", "localID", "money", "coin", "floats", "integers"]
                )
                if has_game_data:
                    td = self.get_token_data(uid)
                    em = td.get("email") if td else None
                    self.save_user_template(uid, real_data, em)
                    log.info(f"load_account: Loaded real data for {uid} ✔")
                    return True

            log.warning(f"load_account: Could not parse real data for {uid}")
            return False

        except Exception as e:
            log.error(f"load_account error for {uid}: {e}")
            return False

    # ── Save full data ────────────────────────────────────────
    async def _send_data(self, auth: str, data: Dict) -> Tuple[bool, str]:
        # Clean data before sending — remove any extra keys not needed
        safe_keys = {
            "Name", "localID", "money", "coin",
            "floats", "integers", "wheels", "animations",
            "personEquipmentsMale", "personEquipmentsFemale",
            "carIDnStatus", "LevelsDoneTime"
        }
        clean_data = {k: v for k, v in data.items() if k in safe_keys}

        r = await self._request(
            SU,
            {"data": json.dumps(clean_data)},
            {"Authorization": f"Bearer {auth}"}
        )
        if r:
            rs = str(r)
            if '"result":1' in rs or "'result': 1" in rs or "1" in rs:
                return True, "OK"
        return False, "SAVE_FAILED"

    async def _save(self, uid: int, data: Dict) -> Dict[str, Any]:
        ok, msg, auth = await self.get_valid_token(uid)
        if not ok:
            return {"ok": False, "message": msg}
        success, msg2 = await self._send_data(auth, data)
        if success:
            td = self.get_token_data(uid)
            self.save_user_template(uid, data, td.get("email") if td else None)
            return {"ok": True}
        return {"ok": False, "message": msg2}

    async def _get_real_data(self, uid: int) -> Dict:
        """
        Always returns real account data.
        Loads from server if not cached.
        """
        loaded = await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        return self.get_user_template(uid, em)

    async def _modify(self, uid: int, mods: Dict[str, Any]) -> Dict[str, Any]:
        """Fixed: Always load real data first before modifying"""
        # Load real data from server first
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)

        for k, v in mods.items():
            if k == "money":
                v = min(v, MAX_MONEY)
            if k == "coin":
                v = min(v, MAX_COIN)
            d[k] = v

        return await self._save(uid, d)

    # ── Game operations ───────────────────────────────────────
    async def set_money(self, uid: int, amount: int) -> Dict[str, Any]:
        return await self._modify(uid, {"money": min(amount, MAX_MONEY)})

    async def set_coin(self, uid: int, amount: int) -> Dict[str, Any]:
        return await self._modify(uid, {"coin": min(amount, MAX_COIN)})

    async def set_player_name(self, uid: int, name: str) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        d["Name"] = name
        return await self._save(uid, d)

    async def set_player_id(self, uid: int, pid: str) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        d["localID"] = pid.upper()
        return await self._save(uid, d)

    async def set_race_wins(self, uid: int, amount: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 9:
            fl.append(0.0)
        fl[8] = float(amount)
        d["floats"] = fl
        return await self._save(uid, d)

    async def set_race_loses(self, uid: int, amount: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 10:
            fl.append(0.0)
        fl[9] = float(amount)
        d["floats"] = fl
        return await self._save(uid, d)

    async def unlock_w16(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 33:
            fl.append(0.0)
        fl[32] = 1.0
        d["floats"] = fl
        return await self._save(uid, d)

    async def unlock_horns(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 32:
            fl.append(0.0)
        for i in [27, 28, 29, 30, 31]:
            fl[i] = 1.0
        d["floats"] = fl
        return await self._save(uid, d)

    async def disable_damage(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 35:
            fl.append(0.0)
        fl[34] = 1.0
        d["floats"] = fl
        return await self._save(uid, d)

    async def unlimited_fuel(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 4:
            fl.append(0.0)
        fl[3] = 1.0
        d["floats"] = fl
        return await self._save(uid, d)

    async def unlock_smoke(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        fl = d.get("floats", [])
        while len(fl) < 34:
            fl.append(0.0)
        fl[33] = 1.0
        d["floats"] = fl
        return await self._save(uid, d)

    async def unlock_animations(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        existing = d.get("animations", [])
        d["animations"] = list(set(existing + list(range(301))))
        return await self._save(uid, d)

    async def unlock_wheels(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        existing_wheels = d.get("wheels", [])
        new_wheels = list(range(73, 221))
        d["wheels"] = list(set(existing_wheels + new_wheels))
        it = d.get("integers", [])
        while len(it) < 113:
            it.append(0)
        for i in [0, 1, 2, 3, 4, 5, 110, 111, 112]:
            it[i] = 1
        d["integers"] = it
        return await self._save(uid, d)

    async def unlock_houses(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        it = d.get("integers", [])
        while len(it) < 113:
            it.append(0)
        for i in [8, 110, 111, 112]:
            it[i] = 1
        d["integers"] = it
        return await self._save(uid, d)

    async def complete_all_levels(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        lvl = [0] + [120 if i == 43 else 1 for i in range(1, 110)]
        d["LevelsDoneTime"] = lvl
        return await self._save(uid, d)

    async def unlock_equipments_male(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        eq = {
            "Gender": 0,
            "bag": list(range(101)),
            "beard": list(range(6, 21)) + [100],
            "cap": list(range(3, 64)),
            "face": [0, 1, 2, 100],
            "glasses": list(range(10)) + [100],
            "gloves": list(range(6)) + [100],
            "hair": list(range(3, 20)) + [100],
            "mask": list(range(3, 9)) + [100],
            "pants": list(range(26)),
            "shoes": list(range(31)),
            "top": list(range(2, 109)),
            "SelectedEquipments": [-1, 10, 19, 41, 100, 4, 20, 9, 22, 21, 74]
        }
        d["personEquipmentsMale"] = eq
        return await self._save(uid, d)

    async def unlock_equipments_female(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)
        eq = {
            "Gender": 1,
            "bag": list(range(6)),
            "beard": [],
            "cap": list(range(3, 41)),
            "face": [0],
            "glasses": list(range(10)),
            "gloves": [1],
            "hair": [0, 7, 8, 9, 10],
            "mask": list(range(3, 8)),
            "pants": list(range(12)),
            "shoes": list(range(3, 15)),
            "top": list(range(5, 80)),
            "SelectedEquipments": [0, 0, -1, -1, -1, -1, -1, -1, 0, -1, -1]
        }
        d["personEquipmentsFemale"] = eq
        return await self._save(uid, d)

    async def set_rank(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        ok, msg, auth = await self.get_valid_token(uid)
        if not ok:
            return {"ok": False, "message": msg}
        rd = {"RatingData": {
            "time": 1e22, "cars": 1e16, "car_fix": 1e13,
            "car_collided": 1e12, "car_exchange": 1e13,
            "car_trade": 1e13, "car_wash": 1e13,
            "slicer_cut": 1e13, "drift_max": 1e14,
            "drift": 1e14, "cargo": 1e5, "delivery": 1e5,
            "race_win": 3e20, "taxi": 1e10,
            "levels": 10000990000, "gifts": 1e9,
            "fuel": 1e10, "offroad": 1e10,
            "speed_banner": 1e9, "reactions": 1e17,
            "run": 1e9, "real_estate": 1e9,
            "t_distance": 1e10, "treasure": 1e10,
            "block_post": 1e10, "push_ups": 1e12,
            "burnt_tire": 1e10, "passanger_distance": 1e8
        }}
        r = await self._request(
            RU,
            {"data": json.dumps(rd)},
            {"Authorization": f"Bearer {auth}"}
        )
        if r and "1" in str(r):
            return {"ok": True}
        return {"ok": False, "message": "RANK_FAILED"}

    async def fix_account_data(self, uid: int) -> Dict[str, Any]:
        await self.load_account(uid)
        td = self.get_token_data(uid)
        em = td.get("email") if td else None
        d = self.get_user_template(uid, em)

        fl = (d.get("floats", []))[:54]
        while len(fl) < 54:
            fl.append(0.0)
        bugs = 0
        fixed_fl = []
        for v in fl:
            if v == 1 or v == 1.0:
                fixed_fl.append(1.0)
            elif isinstance(v, (int, float)) and v > 1:
                bugs += 1
                fixed_fl.append(0.0)
            else:
                fixed_fl.append(float(v) if v else 0.0)

        it = (d.get("integers", []))[:120]
        while len(it) < 120:
            it.append(0)
        fixed_it = []
        for v in it:
            if v == 1:
                fixed_it.append(1)
            elif isinstance(v, (int, float)) and v > 1:
                bugs += 1
                fixed_it.append(0)
            else:
                fixed_it.append(int(v) if v else 0)

        d["floats"] = fixed_fl
        d["integers"] = fixed_it
        result = await self._save(uid, d)
        if result.get("ok"):
            return {"ok": True, "bugs_fixed": bugs}
        return {"ok": False, "message": "FIX_FAILED"}
