"""
================================================================================
 TUGAS UAS TEKNIK KOMPILASI
 Representasi Tahapan Kompilasi untuk Konstruksi Perulangan (WHILE Loop)
================================================================================

 Program ini menyimulasikan EMPAT tahapan utama dalam proses kompilasi
 untuk sebuah konstruksi perulangan `while`:

   1. ANALISIS LEKSIKAL  -> memecah source code menjadi token (lexer).
   2. ANALISIS SINTAKSIS  -> menyusun token menjadi Abstract Syntax Tree (AST)
                             dengan metode Recursive Descent Parser.
   3. ANALISIS SEMANTIK   -> pengecekan dasar memakai Symbol Table
                             (variabel harus dideklarasikan, tipe data cocok,
                              tidak boleh deklarasi ganda).
   4. GENERASI KODE (TAC) -> menghasilkan Three-Address Code dari AST,
                             lengkap dengan variabel temporer (t1, t2, ...)
                             dan label lompatan (L1, L2, ...).

 Bahasa mini yang didukung (subset bahasa mirip C):
   - Deklarasi   : int <var> = <expr> ;
   - Assignment  : <var> = <expr> ;
   - Perulangan  : while ( <kondisi> ) { <statements> }
   - Ekspresi    : aritmatika ( + - * / ) dengan presedensi yang benar
   - Kondisi     : operator relasional ( < > <= >= == != )

 Cara menjalankan:
   python compiler.py            -> memakai contoh bawaan
   python compiler.py file.txt   -> mengompilasi file sumber milik Anda

 Penulis : Fathir Mohammad Noer (221011402223)
================================================================================
"""

import sys
import re


# =============================================================================
# TAHAP 1 - ANALISIS LEKSIKAL (LEXER)
# -----------------------------------------------------------------------------
# Tujuan: mengubah deretan karakter (source code) menjadi deretan TOKEN.
# Setiap token punya: tipe (jenis), nilai (lexeme), serta baris & kolom
# untuk keperluan pesan error yang informatif.
# =============================================================================

# Daftar kata kunci (keyword) yang dikenali oleh bahasa mini ini.
KEYWORDS = {"int", "while"}


class Token:
    """Representasi satu token hasil analisis leksikal."""

    def __init__(self, type_, value, line, col):
        self.type = type_      # contoh: KEYWORD, ID, NUMBER, OP, LPAREN, ...
        self.value = value     # teks asli token, contoh: "while", "x", "10"
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type:<8}, {self.value!r})"


# Spesifikasi token: pasangan (NAMA_TIPE, pola_regex).
# Urutan PENTING: operator multi-karakter (==, <=, >=, !=) harus diuji
# sebelum operator satu-karakter (=, <, >) supaya tidak salah pecah.
TOKEN_SPEC = [
    ("NUMBER",   r"\d+(?:\.\d+)?"),                 # bilangan: 10, 3.14
    ("ID",       r"[A-Za-z_][A-Za-z0-9_]*"),        # identifier / keyword
    ("OP",       r"==|!=|<=|>=|<|>|\+|\-|\*|/|="),   # operator
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("SEMI",     r";"),
    ("NEWLINE",  r"\n"),
    ("SKIP",     r"[ \t\r]+"),                       # spasi/tab -> diabaikan
    ("MISMATCH", r"."),                              # karakter tak dikenal
]

# Gabungkan semua pola menjadi satu regex besar dengan named group.
MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC)
)


class LexerError(Exception):
    pass


def tokenize(source):
    """Mengubah string source code menjadi list of Token."""
    tokens = []
    line = 1
    line_start = 0  # indeks karakter awal baris saat ini (untuk hitung kolom)

    for match in MASTER_PATTERN.finditer(source):
        kind = match.lastgroup
        value = match.group()
        col = match.start() - line_start + 1

        if kind == "NEWLINE":
            line += 1
            line_start = match.end()
            continue
        elif kind == "SKIP":
            continue
        elif kind == "MISMATCH":
            raise LexerError(
                f"[Leksikal] Karakter tidak dikenal {value!r} "
                f"pada baris {line}, kolom {col}"
            )
        elif kind == "ID" and value in KEYWORDS:
            # Identifier yang ternyata kata kunci -> ubah tipe jadi KEYWORD.
            tokens.append(Token("KEYWORD", value, line, col))
        elif kind == "OP":
            tokens.append(Token("OP", value, line, col))
        else:
            tokens.append(Token(kind, value, line, col))

    # Token penanda akhir input, memudahkan parser.
    tokens.append(Token("EOF", "<eof>", line, 0))
    return tokens


# =============================================================================
# TAHAP 2 - ANALISIS SINTAKSIS (PARSER)
# -----------------------------------------------------------------------------
# Tujuan: memeriksa apakah deretan token mengikuti aturan tata bahasa (grammar),
# lalu membangun Abstract Syntax Tree (AST).
#
# Grammar (notasi BNF) yang diparsing:
#
#   <program>   ::= { <stmt> }
#   <stmt>      ::= <decl> | <assign> | <while>
#   <decl>      ::= "int" <id> "=" <expr> ";"
#   <assign>    ::= <id> "=" <expr> ";"
#   <while>     ::= "while" "(" <cond> ")" "{" { <stmt> } "}"
#   <cond>      ::= <expr> <relop> <expr>
#   <expr>      ::= <term> { ("+" | "-") <term> }
#   <term>      ::= <factor> { ("*" | "/") <factor> }
#   <factor>    ::= <id> | <number> | "(" <expr> ")"
#   <relop>     ::= "<" | ">" | "<=" | ">=" | "==" | "!="
#
# Metode: Recursive Descent Parser (satu fungsi per aturan grammar).
# =============================================================================

# ---- Node-node AST ----------------------------------------------------------
class Program:
    def __init__(self, statements):
        self.statements = statements


class VarDecl:
    """Deklarasi variabel, contoh: int x = 0 ;"""
    def __init__(self, var_type, name, expr):
        self.var_type = var_type
        self.name = name
        self.expr = expr


class Assign:
    """Penugasan nilai, contoh: x = x + 1 ;"""
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr


class While:
    def __init__(self, cond, body):
        self.cond = cond      # node BinOp dengan operator relasional
        self.body = body      # list of stmt


class BinOp:
    """Operasi biner: aritmatika atau relasional."""
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class Num:
    def __init__(self, value):
        self.value = value


class Var:
    def __init__(self, name):
        self.name = name


RELATIONAL = {"<", ">", "<=", ">=", "==", "!="}


class ParserError(Exception):
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---- Utilitas navigasi token ----
    @property
    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, type_, value=None):
        """Pastikan token sekarang sesuai harapan; jika tidak -> error sintaksis."""
        tok = self.current
        if tok.type != type_ or (value is not None and tok.value != value):
            harapan = value if value is not None else type_
            raise ParserError(
                f"[Sintaksis] Mengharapkan {harapan!r} tetapi menemukan "
                f"{tok.value!r} pada baris {tok.line}, kolom {tok.col}"
            )
        return self.advance()

    # ---- Aturan grammar ----
    def parse(self):
        """<program> ::= { <stmt> }"""
        statements = []
        while self.current.type != "EOF":
            statements.append(self.statement())
        return Program(statements)

    def statement(self):
        """<stmt> ::= <decl> | <assign> | <while>"""
        tok = self.current
        if tok.type == "KEYWORD" and tok.value == "int":
            return self.declaration()
        elif tok.type == "KEYWORD" and tok.value == "while":
            return self.while_stmt()
        elif tok.type == "ID":
            return self.assignment()
        else:
            raise ParserError(
                f"[Sintaksis] Statement tidak valid diawali {tok.value!r} "
                f"pada baris {tok.line}, kolom {tok.col}"
            )

    def declaration(self):
        """<decl> ::= "int" <id> "=" <expr> ";" """
        var_type = self.expect("KEYWORD", "int").value
        name = self.expect("ID").value
        self.expect("OP", "=")
        expr = self.expression()
        self.expect("SEMI")
        return VarDecl(var_type, name, expr)

    def assignment(self):
        """<assign> ::= <id> "=" <expr> ";" """
        name = self.expect("ID").value
        self.expect("OP", "=")
        expr = self.expression()
        self.expect("SEMI")
        return Assign(name, expr)

    def while_stmt(self):
        """<while> ::= "while" "(" <cond> ")" "{" { <stmt> } "}" """
        self.expect("KEYWORD", "while")
        self.expect("LPAREN")
        cond = self.condition()
        self.expect("RPAREN")
        self.expect("LBRACE")
        body = []
        while self.current.type != "RBRACE":
            if self.current.type == "EOF":
                raise ParserError("[Sintaksis] Blok while tidak ditutup '}'")
            body.append(self.statement())
        self.expect("RBRACE")
        return While(cond, body)

    def condition(self):
        """<cond> ::= <expr> <relop> <expr>"""
        left = self.expression()
        op = self.current
        if op.type != "OP" or op.value not in RELATIONAL:
            raise ParserError(
                f"[Sintaksis] Mengharapkan operator relasional tetapi menemukan "
                f"{op.value!r} pada baris {op.line}, kolom {op.col}"
            )
        self.advance()
        right = self.expression()
        return BinOp(op.value, left, right)

    def expression(self):
        """<expr> ::= <term> { ("+" | "-") <term> }"""
        node = self.term()
        while self.current.type == "OP" and self.current.value in ("+", "-"):
            op = self.advance().value
            right = self.term()
            node = BinOp(op, node, right)
        return node

    def term(self):
        """<term> ::= <factor> { ("*" | "/") <factor> }"""
        node = self.factor()
        while self.current.type == "OP" and self.current.value in ("*", "/"):
            op = self.advance().value
            right = self.factor()
            node = BinOp(op, node, right)
        return node

    def factor(self):
        """<factor> ::= <id> | <number> | "(" <expr> ")" """
        tok = self.current
        if tok.type == "NUMBER":
            self.advance()
            return Num(tok.value)
        elif tok.type == "ID":
            self.advance()
            return Var(tok.value)
        elif tok.type == "LPAREN":
            self.advance()
            node = self.expression()
            self.expect("RPAREN")
            return node
        else:
            raise ParserError(
                f"[Sintaksis] Faktor tidak valid {tok.value!r} "
                f"pada baris {tok.line}, kolom {tok.col}"
            )


def render_ast(node, indent=0):
    """Mencetak AST dalam bentuk pohon yang mudah dibaca manusia."""
    pad = "    " * indent
    if isinstance(node, Program):
        lines = [f"{pad}Program"]
        for stmt in node.statements:
            lines.append(render_ast(stmt, indent + 1))
        return "\n".join(lines)
    if isinstance(node, VarDecl):
        lines = [f"{pad}VarDecl (type={node.var_type}, name={node.name})"]
        lines.append(render_ast(node.expr, indent + 1))
        return "\n".join(lines)
    if isinstance(node, Assign):
        lines = [f"{pad}Assign (name={node.name})"]
        lines.append(render_ast(node.expr, indent + 1))
        return "\n".join(lines)
    if isinstance(node, While):
        lines = [f"{pad}While"]
        lines.append(f"{pad}    Condition:")
        lines.append(render_ast(node.cond, indent + 2))
        lines.append(f"{pad}    Body:")
        for stmt in node.body:
            lines.append(render_ast(stmt, indent + 2))
        return "\n".join(lines)
    if isinstance(node, BinOp):
        lines = [f"{pad}BinOp ({node.op})"]
        lines.append(render_ast(node.left, indent + 1))
        lines.append(render_ast(node.right, indent + 1))
        return "\n".join(lines)
    if isinstance(node, Num):
        return f"{pad}Num ({node.value})"
    if isinstance(node, Var):
        return f"{pad}Var ({node.name})"
    return f"{pad}<?>"


# =============================================================================
# TAHAP 3 - ANALISIS SEMANTIK
# -----------------------------------------------------------------------------
# Tujuan: memeriksa "makna" program memakai Symbol Table, antara lain:
#   - sebuah variabel tidak boleh dideklarasikan dua kali,
#   - variabel harus sudah dideklarasikan sebelum dipakai/diberi nilai,
#   - tipe operand pada ekspresi harus cocok (di sini semuanya 'int').
# =============================================================================

class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = {}   # nama_variabel -> tipe
        self.log = []            # catatan langkah pemeriksaan

    def analyze(self, program):
        for stmt in program.statements:
            self.visit(stmt)
        return self.symbol_table

    def visit(self, node):
        if isinstance(node, VarDecl):
            if node.name in self.symbol_table:
                raise SemanticError(
                    f"[Semantik] Variabel '{node.name}' dideklarasikan ulang."
                )
            t = self.eval_type(node.expr)
            if t != node.var_type:
                raise SemanticError(
                    f"[Semantik] Ketidakcocokan tipe pada '{node.name}': "
                    f"dideklarasikan '{node.var_type}' tetapi nilainya '{t}'."
                )
            self.symbol_table[node.name] = node.var_type
            self.log.append(f"deklarasi '{node.name}' : {node.var_type}  -> OK")

        elif isinstance(node, Assign):
            if node.name not in self.symbol_table:
                raise SemanticError(
                    f"[Semantik] Variabel '{node.name}' dipakai sebelum "
                    f"dideklarasikan."
                )
            self.eval_type(node.expr)
            self.log.append(f"assignment '{node.name}'  -> OK")

        elif isinstance(node, While):
            self.eval_type(node.cond)  # validasi variabel dalam kondisi
            self.log.append("kondisi while diperiksa  -> OK")
            for stmt in node.body:
                self.visit(stmt)

    def eval_type(self, node):
        """Mengembalikan tipe sebuah ekspresi sambil memvalidasi operand."""
        if isinstance(node, Num):
            return "int"
        if isinstance(node, Var):
            if node.name not in self.symbol_table:
                raise SemanticError(
                    f"[Semantik] Variabel '{node.name}' belum dideklarasikan."
                )
            return self.symbol_table[node.name]
        if isinstance(node, BinOp):
            lt = self.eval_type(node.left)
            rt = self.eval_type(node.right)
            if lt != rt:
                raise SemanticError(
                    f"[Semantik] Operasi '{node.op}' antara tipe berbeda "
                    f"({lt} dan {rt})."
                )
            return lt
        raise SemanticError("[Semantik] Node ekspresi tidak dikenal.")


# =============================================================================
# TAHAP 4 - GENERASI KODE ANTARA (THREE-ADDRESS CODE / TAC)
# -----------------------------------------------------------------------------
# Tujuan: menerjemahkan AST menjadi instruksi sederhana berbentuk
#   x = y op z
# Setiap sub-ekspresi disimpan ke variabel temporer (t1, t2, ...),
# dan struktur perulangan diterjemahkan memakai label (L1, L2, ...) + goto.
# =============================================================================

class TACGenerator:
    def __init__(self):
        self.code = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self):
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self):
        self.label_counter += 1
        return f"L{self.label_counter}"

    def emit(self, instruction):
        self.code.append(instruction)

    def generate(self, program):
        for stmt in program.statements:
            self.gen_stmt(stmt)
        return self.code

    def gen_stmt(self, node):
        if isinstance(node, (VarDecl, Assign)):
            place = self.gen_expr(node.expr)
            self.emit(f"{node.name} = {place}")

        elif isinstance(node, While):
            label_start = self.new_label()
            label_end = self.new_label()
            self.emit(f"{label_start}:")
            cond_place = self.gen_expr(node.cond)
            self.emit(f"ifFalse {cond_place} goto {label_end}")
            for stmt in node.body:
                self.gen_stmt(stmt)
            self.emit(f"goto {label_start}")
            self.emit(f"{label_end}:")

    def gen_expr(self, node):
        """Menghasilkan TAC untuk ekspresi, mengembalikan 'tempat' nilainya."""
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Var):
            return node.name
        if isinstance(node, BinOp):
            left = self.gen_expr(node.left)
            right = self.gen_expr(node.right)
            temp = self.new_temp()
            self.emit(f"{temp} = {left} {node.op} {right}")
            return temp
        raise RuntimeError("Node ekspresi tidak dikenal saat generasi TAC.")


# =============================================================================
# DRIVER UTAMA — menjalankan keempat tahap dan menampilkan hasilnya.
# =============================================================================

def garis(judul):
    return f"\n{'=' * 70}\n {judul}\n{'=' * 70}"


def compile_source(source):
    print(garis("SOURCE CODE (INPUT)"))
    print(source.strip())

    # --- Tahap 1: Leksikal ---
    print(garis("TAHAP 1 - ANALISIS LEKSIKAL (DAFTAR TOKEN)"))
    tokens = tokenize(source)
    for i, tok in enumerate(tokens):
        print(f"  {i:>2}. {tok}")

    # --- Tahap 2: Sintaksis ---
    print(garis("TAHAP 2 - ANALISIS SINTAKSIS (ABSTRACT SYNTAX TREE)"))
    ast = Parser(tokens).parse()
    print(render_ast(ast))

    # --- Tahap 3: Semantik ---
    print(garis("TAHAP 3 - ANALISIS SEMANTIK (SYMBOL TABLE & PEMERIKSAAN)"))
    analyzer = SemanticAnalyzer()
    symbol_table = analyzer.analyze(ast)
    print("  Langkah pemeriksaan:")
    for entry in analyzer.log:
        print(f"    - {entry}")
    print("\n  Symbol Table akhir:")
    print(f"    {'NAMA':<10}{'TIPE':<10}")
    print(f"    {'-' * 18}")
    for name, t in symbol_table.items():
        print(f"    {name:<10}{t:<10}")

    # --- Tahap 4: Generasi TAC ---
    print(garis("TAHAP 4 - GENERASI KODE ANTARA (THREE-ADDRESS CODE)"))
    tac = TACGenerator().generate(ast)
    for i, line in enumerate(tac, start=1):
        # Label rata kiri, instruksi biasa diberi indentasi.
        if line.endswith(":"):
            print(f"  {line}")
        else:
            print(f"      {i:>2}: {line}")

    print(garis("KOMPILASI SELESAI - semua tahap berhasil."))


# Contoh bawaan: menjumlahkan angka 0..9 memakai perulangan while.
DEFAULT_SOURCE = """
int i = 0;
int sum = 0;
while (i < 10) {
    sum = sum + i * 2;
    i = i + 1;
}
"""


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
        except OSError as e:
            print(f"Gagal membuka file {path!r}: {e}")
            sys.exit(1)
    else:
        source = DEFAULT_SOURCE

    try:
        compile_source(source)
    except (LexerError, ParserError, SemanticError) as e:
        print(garis("KOMPILASI GAGAL"))
        print(f"  {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
