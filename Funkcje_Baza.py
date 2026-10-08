import pymysql
from datetime import date

from Connect import mydb
from dates import parse_issue_date
from konwersje import (
    convert_to_dict,
    convert_to_dict_dst,
    convert_to_dict_odb,
    convert_to_dict_PZ,
    convert_to_dict_WZ,
)
from vat import net_price, quantity, totals_from_net, vat_rate


def select_tow():
    cur = mydb.cursor()
    cur.execute("SELECT tow_kod, tow_name, ilo_is, ce, vat_rate, added_at, modified_at FROM tow ORDER BY tow_kod DESC;")
    tow = cur.fetchall()
    return tow

def select_tow_where(tow):
    cur = mydb.cursor()
    query_select = 'SELECT tow_kod FROM tow where tow_kod = %s;'
    cur.execute(query_select, tow)
    result = cur.fetchall()
    return result[0][0] if result else False


def select_WZ():
    cur = mydb.cursor()
    cur.execute("""
        SELECT wz.idwz, wz.issue_date, COALESCE(totals.net, 0), COALESCE(totals.vat, 0),
               COALESCE(totals.net, 0) + COALESCE(totals.vat, 0), odb.name_odb
        FROM wz JOIN odb ON wz.odb_kod_odb = odb.kod_odb
        LEFT JOIN (
            SELECT wz_idwz, SUM(CAST(val AS DECIMAL(18,2))) AS net,
                   SUM(ROUND(CAST(val AS DECIMAL(18,2)) * vat_rate / 100, 2)) AS vat
            FROM wz_p GROUP BY wz_idwz
        ) AS totals ON totals.wz_idwz = wz.idwz;
    """)
    WZ = cur.fetchall()
    return WZ

def select_WZ_where(WZ):
    cur = mydb.cursor()
    query_select = 'SELECT wz.idwz FROM WZ where wz.idwz = %s;'
    cur.execute(query_select, WZ)
    WZ = cur.fetchall()
    #tow = tow[0]
    #tow = tow[0]
    print(WZ)
    return WZ

def select_PZ():
    cur = mydb.cursor()
    cur.execute("""
        SELECT pz.idpz, pz.issue_date, COALESCE(totals.net, 0), COALESCE(totals.vat, 0),
               COALESCE(totals.net, 0) + COALESCE(totals.vat, 0), dst.name_dst
        FROM pz JOIN dst ON pz.dst_kod_dst = dst.kod_dst
        LEFT JOIN (
            SELECT pz_idpz, SUM(CAST(val AS DECIMAL(18,2))) AS net,
                   SUM(ROUND(CAST(val AS DECIMAL(18,2)) * vat_rate / 100, 2)) AS vat
            FROM pz_p GROUP BY pz_idpz
        ) AS totals ON totals.pz_idpz = pz.idpz;
    """)
    PZ = cur.fetchall()
    return PZ



def select_PZ_where(pz):
    cur = mydb.cursor()
    query_select = 'SELECT pz.idpz FROM pz where pz.idpz = %s;'
    cur.execute(query_select, pz)
    pz = cur.fetchall()
    #tow = tow[0]
    #tow = tow[0]
    #print(PZ)
    return pz

def select_odb_where(kod):
    cur = mydb.cursor()
    query_select = 'SELECT kod_odb FROM odb where kod_odb = %s;'
    cur.execute(query_select, kod)
    result = cur.fetchall()
    return result[0][0] if result else False


def select_dst_where(kod):
    cur = mydb.cursor()
    query_select = 'SELECT kod_dst FROM dst where kod_dst = %s;'
    cur.execute(query_select, kod)
    result = cur.fetchall()
    return result[0][0] if result else False


_NEXT_CODE_QUERIES = {
    "tow": "SELECT MAX(CAST(tow_kod AS DECIMAL(45, 0))) FROM tow WHERE tow_kod REGEXP '^[0-9]+$'",
    "odb": "SELECT MAX(kod_odb) FROM odb",
    "dst": "SELECT MAX(kod_dst) FROM dst",
}


def select_next_code(entity):
    """Suggest the next numeric code without changing any existing codes."""
    cur = mydb.cursor()
    cur.execute(_NEXT_CODE_QUERIES[entity])
    highest = cur.fetchone()[0]
    return str(max(int(highest or 0), 0) + 1)


def delete_tow(tow):
    cur = mydb.cursor()
    query_del = "delete from tow where tow_kod = %s;"
    cur.execute(query_del, tow)
    mydb.commit()

def delete_odb(odb):
    cur = mydb.cursor()
    query_del = "delete from odb where kod_odb = %s;"
    cur.execute(query_del,odb)
    mydb.commit()

def delete_dst(dst):
    cur = mydb.cursor()
    query_del = "delete from dst where kod_dst = %s;"
    cur.execute(query_del,dst)
    mydb.commit()

def delete_WZ(WZ):
    WZ = WZ
    cur = mydb.cursor()
    query_sel2 = "select tow_tow_kod, ilo from wz_p where wz_idwz = %s;"
    query_sel = "select tow_kod, ilo_is from tow where tow_kod = %s;"
    query_upd = "update tow set ilo_is = %s where tow_kod = %s;"
    query_del = "delete from wz where idwz = %s;"
    query_del2 = "delete from wz_p where wz_idwz = %s;"
    cur.execute(query_sel2, WZ)
    wz_p = cur.fetchall()
    print(wz_p)
    for x in wz_p:
        cur.execute(query_sel, x[0])
        tow = cur.fetchall()[0]
        print(tow)
        print(x)
        ilo_is = tow[1] + x[1]
        cur.execute(query_upd, (ilo_is, x[0]))
    cur.execute(query_del2,WZ)
    cur.execute(query_del,WZ)
    mydb.commit()

def delete_PZ(PZ):
    cur = mydb.cursor()
    query_sel2 = "select tow_tow_kod, ilo from pz_p where pz_idpz = %s;"
    query_sel = "select tow_kod, ilo_is from tow where tow_kod = %s;"
    query_upd = "update tow set ilo_is = %s where tow_kod = %s;"
    query_del = "delete from pz where idpz = %s;"
    query_del2 = "delete from pz_p where pz_idpz = %s;"
    cur.execute(query_sel2, PZ)
    pz_p = cur.fetchall()
    # print(len(wz_p))
    for x in pz_p:
        cur.execute(query_sel, x[0])
        tow = cur.fetchall()[0]
        ilo_is = tow[1] - x[1]
        cur.execute(query_upd, (ilo_is, x[0]))
    cur.execute(query_del2, PZ)
    cur.execute(query_del, PZ)
    mydb.commit()


def add_tow(tow_kod, nazwa, ce, vat=0):
    cur = mydb.cursor()
    query_add = "insert into tow (tow_kod, tow_name, ilo_is, ce, vat_rate, added_at) values (%s,%s,0,%s,%s,NOW());"
    try:
        cur.execute(query_add, (tow_kod, nazwa, net_price(ce), vat_rate(vat)))
        mydb.commit()
    except pymysql.err.IntegrityError as error:
        mydb.rollback()
        if error.args[0] == 1062:
            return True
        raise
    return False

def display_data_in_table(self, dane_tow):
    from prettytable import PrettyTable

    table = PrettyTable()
    table.field_names = ["Towar", "Kod", "Ilość", "Cena"]

    for item in dane_tow:
        table.add_row([item['tow_name'], item['tow_kod'], item['ilo_is'], item['ce']])
    return table

def select_tow2():
    return [tuple(row) for row in select_tow()]

def select_odb():
    cur = mydb.cursor()
    cur.execute("SELECT kod_odb, name_odb, nip FROM odb ORDER BY kod_odb DESC;")
    odb = cur.fetchall()
    return odb


def select_odb2():
    return [tuple(row) for row in select_odb()]


def select_dst():
    cur = mydb.cursor()
    cur.execute("SELECT kod_dst, name_dst, nip FROM dst ORDER BY kod_dst DESC;")
    dst = cur.fetchall()
    return dst


def select_dst2():
    return [tuple(row) for row in select_dst()]

def select_WZ2():
    return [tuple(row) for row in select_WZ()]

def select_PZ2():
    return [tuple(row) for row in select_PZ()]


def zamien_przecinek_na_kropke(tekst):
    return tekst.replace(',', '.')


def add_odb(kod, nazwa, nip):
    cur = mydb.cursor()
    query_add = "insert into odb (kod_odb, name_odb, nip) values (%s,%s,%s);"
    try:
        cur.execute(query_add, (kod, nazwa, nip))
        mydb.commit()
    except pymysql.err.IntegrityError as error:
        mydb.rollback()
        if error.args[0] == 1062:
            return True
        raise
    return False


def add_dst(kod, nazwa, nip):
    cur = mydb.cursor()
    query_add = "insert into dst (kod_dst, name_dst, nip) values (%s,%s,%s);"
    try:
        cur.execute(query_add, (kod, nazwa, nip))
        mydb.commit()
    except pymysql.err.IntegrityError as error:
        mydb.rollback()
        if error.args[0] == 1062:
            return True
        raise
    return False

def tow_edit(kod, nazwa, cena, vat):
    cur = mydb.cursor()
    kod = kod.replace('Kod: ', '')
    queue_update = "UPDATE tow SET tow_name = %s, ce = %s, vat_rate = %s, modified_at = NOW() WHERE tow_kod = %s"
    cur.execute(queue_update, (nazwa, net_price(cena), vat_rate(vat), kod))
    mydb.commit()

def dst_edit(kod, nazwa, nip):
    cur = mydb.cursor()
    kod = kod.replace('Kod: ', '')
    queue_update = "update dst set name_dst = %s , nip = %s where kod_dst = %s"
    cur.execute(queue_update, (nazwa, nip, kod))
    mydb.commit()

def odb_edit(kod, nazwa, nip):
    cur = mydb.cursor()
    kod = kod.replace('Kod: ', '')
    queue_update = "update odb set name_odb = %s , nip = %s where kod_odb = %s"
    cur.execute(queue_update, (nazwa, nip, kod))
    mydb.commit()


def _update_stock(cur, code, delta):
    cur.execute("SELECT ilo_is FROM tow WHERE tow_kod = %s FOR UPDATE", (code,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Towar {code} nie istnieje w bazie.")
    new_quantity = float(row[0] or 0) + delta
    if new_quantity < 0:
        raise ValueError(f"Za mało towaru {code} na stanie.")
    cur.execute("UPDATE tow SET ilo_is = %s WHERE tow_kod = %s", (new_quantity, code))


def _write_document_lines(cur, kind, document_id, lines):
    table, reference, stock_sign = {
        "wz": ("wz_p", "wz_idwz", -1),
        "pz": ("pz_p", "pz_idpz", 1),
    }[kind]
    total_net = 0
    for code, _name, _price, amount, saved_net, rate in lines:
        amount = quantity(amount)
        net, _tax, _gross = totals_from_net(saved_net, rate)
        if net < 0:
            raise ValueError("Wartość netto pozycji nie może być ujemna.")
        _update_stock(cur, code, stock_sign * amount)
        cur.execute(
            f"INSERT INTO {table} (val, vat_rate, tow_tow_kod, {reference}, ilo) VALUES (%s,%s,%s,%s,%s)",
            (net, vat_rate(rate), code, document_id, amount),
        )
        total_net += net
    return total_net


def _add_document(kind, lines, partner_code, document_date=None):
    if not lines:
        raise ValueError("Dokument musi zawierać co najmniej jedną pozycję.")
    table, partner_column = {
        "wz": ("wz", "odb_kod_odb"),
        "pz": ("pz", "dst_kod_dst"),
    }[kind]
    document_date = date.today() if document_date is None else parse_issue_date(document_date)
    cur = mydb.cursor()
    try:
        cur.execute(
            f"INSERT INTO {table} ({partner_column}, dok_id, issue_date) VALUES (%s,%s,%s)",
            (partner_code, kind, document_date),
        )
        document_id = cur.lastrowid
        total_net = _write_document_lines(cur, kind, document_id, lines)
        cur.execute(f"UPDATE {table} SET val = %s WHERE id{kind} = %s", (total_net, document_id))
        mydb.commit()
        return document_id
    except Exception:
        mydb.rollback()
        raise


def add_wz(pozycje, odb, document_date=None):
    return _add_document("wz", pozycje, odb, document_date)


def add_pz(pozycje, dst, tow_ilo_ost=None, document_date=None):
    return _add_document("pz", pozycje, dst, document_date)


def ilo_check(tow):
    cur = mydb.cursor()
    query_select_ilo = "select ilo_is from tow where tow_kod = %s"
    cur.execute(query_select_ilo, tow)
    ilo = cur.fetchall()
    if ilo == ():
        ilo = 1
    else:
        ilo = ilo[0]
        ilo = ilo[0]
    return ilo

def select_pz_edit(pz):
    cur = mydb.cursor()
    query_select_pz = "select dst_kod_dst, issue_date from pz where idpz = %s"
    print(pz)
    query_select_pz_p = "SELECT pz_p.ilo, pz_p.val, pz_p.tow_tow_kod, tow.tow_name, COALESCE(pz_p.val / NULLIF(pz_p.ilo, 0), tow.ce), pz_p.vat_rate FROM pz_p LEFT JOIN tow ON pz_p.tow_tow_kod = tow.tow_kod WHERE pz_idpz = %s"
    cur.execute(query_select_pz, pz)
    x_pz = cur.fetchall()
    cur.execute(query_select_pz_p, pz)
    y_pz = cur.fetchall()
    return x_pz, y_pz

def select_wz_edit(wz):
    cur = mydb.cursor()
    query_select_wz = "select odb_kod_odb, issue_date from wz where idwz = %s"
    print(wz)
    query_select_wz_p = "SELECT wz_p.ilo, wz_p.val, wz_p.tow_tow_kod, tow.tow_name, COALESCE(wz_p.val / NULLIF(wz_p.ilo, 0), tow.ce), wz_p.vat_rate FROM wz_p LEFT JOIN tow ON wz_p.tow_tow_kod = tow.tow_kod WHERE wz_idwz = %s"
    cur.execute(query_select_wz, wz)
    x_wz = cur.fetchall()
    cur.execute(query_select_wz_p, wz)
    y_wz = cur.fetchall()
    return x_wz, y_wz

def del_pz_p(PZ):
    cur = mydb.cursor()
    query_del2 = "delete from pz_p where pz_idpz = %s;"
    cur.execute(query_del2, PZ)
    mydb.commit()

def del_wz_p(WZ):
    cur = mydb.cursor()
    query_del2 = "delete from wz_p where wz_idwz = %s;"
    cur.execute(query_del2, WZ)
    mydb.commit()


def _edit_document(kind, lines, document_id, partner_code=None, document_date=None):
    if not lines:
        raise ValueError("Dokument musi zawierać co najmniej jedną pozycję.")
    if document_date is not None:
        document_date = parse_issue_date(document_date)
    header, line_table, reference, partner_column, stock_sign = {
        "wz": ("wz", "wz_p", "wz_idwz", "odb_kod_odb", -1),
        "pz": ("pz", "pz_p", "pz_idpz", "dst_kod_dst", 1),
    }[kind]
    cur = mydb.cursor()
    try:
        cur.execute(
            f"SELECT tow_tow_kod, ilo FROM {line_table} WHERE {reference} = %s FOR UPDATE",
            (document_id,),
        )
        for code, amount in cur.fetchall():
            _update_stock(cur, code, -stock_sign * int(amount))
        cur.execute(f"DELETE FROM {line_table} WHERE {reference} = %s", (document_id,))
        total_net = _write_document_lines(cur, kind, document_id, lines)
        assignments = ["val = %s"]
        values = [total_net]
        if partner_code is not None:
            assignments.append(f"{partner_column} = %s")
            values.append(partner_code)
        if document_date is not None:
            assignments.append("issue_date = %s")
            values.append(document_date)
        values.append(document_id)
        cur.execute(
            f"UPDATE {header} SET {', '.join(assignments)} WHERE id{kind} = %s",
            tuple(values),
        )
        mydb.commit()
    except Exception:
        mydb.rollback()
        raise


def edit_pz(pozycje, pz, dst=None, document_date=None):
    _edit_document("pz", pozycje, pz, dst, document_date)


def edit_wz(pozycje, wz, odb=None, document_date=None):
    _edit_document("wz", pozycje, wz, odb, document_date)
