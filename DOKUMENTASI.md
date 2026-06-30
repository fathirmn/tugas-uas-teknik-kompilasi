# Dokumentasi Tugas UAS Teknik Kompilasi
## Representasi Tahapan Kompilasi pada Konstruksi Perulangan (`while` Loop)

**Nama:** Fathir Mohammad Noer
**NIM:** 221011402223
**Mata Kuliah:** Teknik Kompilasi
**Konstruksi yang dipilih:** Perulangan (*Looping*) — `while`

---

## 1. Pendahuluan

Dokumen ini menjelaskan implementasi sebuah *mini-compiler* yang menyimulasikan
empat tahapan utama dalam proses kompilasi sebuah program, yaitu:

1. **Analisis Leksikal** (*Lexical Analysis*)
2. **Analisis Sintaksis** (*Syntax Analysis*)
3. **Analisis Semantik** (*Semantic Analysis*)
4. **Generasi Kode Antara** (*Three-Address Code* / TAC)

Konstruksi bahasa yang dipilih adalah **perulangan `while`**. Konstruksi ini
dipilih karena memperlihatkan dengan jelas bagaimama sebuah struktur kontrol
(*control flow*) diterjemahkan menjadi instruksi tingkat rendah berbentuk
**label** dan **lompatan (`goto`)** pada tahap generasi kode.

Program ditulis dengan bahasa **Python 3** (tanpa *library* eksternal) dan
seluruh tahapan dibuat dari nol agar setiap proses terlihat eksplisit.

---

## 2. Bahasa Mini yang Didukung

Program menerima *subset* kecil bahasa mirip C dengan aturan berikut:

| Konstruksi   | Bentuk                                    | Contoh                       |
|--------------|-------------------------------------------|------------------------------|
| Deklarasi    | `int <var> = <expr> ;`                    | `int i = 0;`                 |
| Assignment   | `<var> = <expr> ;`                        | `i = i + 1;`                 |
| Perulangan   | `while ( <kondisi> ) { <statements> }`    | `while (i < 10) { ... }`     |
| Ekspresi     | aritmatika `+ - * /` (presedensi benar)   | `sum + i * 2`                |
| Kondisi      | relasional `< > <= >= == !=`              | `i < 10`                     |

### Contoh program masukan (`contoh.txt`)

```c
int i = 0;
int sum = 0;
while (i < 10) {
    sum = sum + i * 2;
    i = i + 1;
}
```

---

## 3. Pattern / Pola Tata Bahasa (Grammar BNF)

Aturan sintaksis konstruksi didefinisikan memakai notasi **Backus–Naur Form (BNF)**.
Notasi `{ ... }` berarti "diulang nol kali atau lebih".

```bnf
<program>   ::= { <stmt> }
<stmt>      ::= <decl> | <assign> | <while>
<decl>      ::= "int" <id> "=" <expr> ";"
<assign>    ::= <id> "=" <expr> ";"
<while>     ::= "while" "(" <cond> ")" "{" { <stmt> } "}"
<cond>      ::= <expr> <relop> <expr>
<expr>      ::= <term>   { ("+" | "-") <term> }
<term>      ::= <factor> { ("*" | "/") <factor> }
<factor>    ::= <id> | <number> | "(" <expr> ")"
<relop>     ::= "<" | ">" | "<=" | ">=" | "==" | "!="
<id>        ::= huruf, { huruf | angka | "_" }
<number>    ::= angka, { angka }
```

> **Catatan presedensi:** pemisahan aturan menjadi `<expr>` → `<term>` → `<factor>`
> membuat perkalian/pembagian (`* /`) otomatis dikerjakan **lebih dulu** daripada
> penjumlahan/pengurangan (`+ -`), sesuai aturan matematika.

Pola token (level leksikal) dapat dinyatakan dengan **Regular Expression**:

```text
NUMBER   ->  \d+(\.\d+)?
ID       ->  [A-Za-z_][A-Za-z0-9_]*
OP       ->  ==|!=|<=|>=|<|>|\+|\-|\*|/|=
SIMBOL   ->  ( ) { } ;
SKIP     ->  spasi / tab / newline   (diabaikan)
```

---

## 4. Tahapan Kompilasi

### 4.1 Analisis Leksikal (*Lexer*)

**Tujuan:** mengubah deretan karakter mentah menjadi deretan **token**
(satuan terkecil yang bermakna). Setiap token menyimpan *tipe*, *nilai (lexeme)*,
serta posisi *baris* dan *kolom* untuk pesan error.

Implementasi memakai satu *master regex* gabungan dari semua pola token.
Kata seperti `int` dan `while` awalnya cocok sebagai `ID`, lalu diperiksa pada
daftar **KEYWORDS** dan diubah tipenya menjadi `KEYWORD`.

**Contoh keluaran (sebagian):**

```
 0. Token(KEYWORD , 'int')
 1. Token(ID      , 'i')
 2. Token(OP      , '=')
 3. Token(NUMBER  , '0')
 4. Token(SEMI    , ';')
10. Token(KEYWORD , 'while')
11. Token(LPAREN  , '(')
...
```

### 4.2 Analisis Sintaksis (*Parser*)

**Tujuan:** memeriksa apakah urutan token mengikuti aturan grammar, lalu
membangun **Abstract Syntax Tree (AST)** — representasi pohon dari struktur program.

Metode yang dipakai adalah **Recursive Descent Parser**: setiap aturan grammar
diwujudkan menjadi satu fungsi (`declaration()`, `while_stmt()`, `expression()`,
`term()`, `factor()`, dst.) yang saling memanggil secara rekursif.

**Contoh AST yang dihasilkan:**

```
Program
    VarDecl (type=int, name=i)
        Num (0)
    VarDecl (type=int, name=sum)
        Num (0)
    While
        Condition:
            BinOp (<)
                Var (i)
                Num (10)
        Body:
            Assign (name=sum)
                BinOp (+)
                    Var (sum)
                    BinOp (*)
                        Var (i)
                        Num (2)
            Assign (name=i)
                BinOp (+)
                    Var (i)
                    Num (1)
```

Perhatikan bahwa `sum + i * 2` membentuk pohon di mana `BinOp (*)` berada
**lebih dalam** daripada `BinOp (+)`. Inilah bukti presedensi operator bekerja.

### 4.3 Analisis Semantik

**Tujuan:** memeriksa "makna" program — hal-hal yang benar secara sintaksis tetapi
salah secara logika. Pemeriksaan memakai **Symbol Table** (tabel simbol), yaitu
struktur data yang mencatat nama variabel beserta tipenya.

Pemeriksaan yang dilakukan:

1. **Deklarasi ganda** — sebuah variabel tidak boleh dideklarasikan dua kali.
2. **Variabel belum dideklarasikan** — variabel harus ada di Symbol Table
   sebelum dipakai atau diberi nilai.
3. **Kecocokan tipe** — operand pada sebuah operasi harus bertipe sama
   (pada bahasa mini ini semuanya `int`).

**Contoh keluaran:**

```
Langkah pemeriksaan:
  - deklarasi 'i' : int  -> OK
  - deklarasi 'sum' : int  -> OK
  - kondisi while diperiksa  -> OK
  - assignment 'sum'  -> OK
  - assignment 'i'  -> OK

Symbol Table akhir:
  NAMA      TIPE
  ------------------
  i         int
  sum       int
```

### 4.4 Generasi Kode Antara (*Three-Address Code*)

**Tujuan:** menerjemahkan AST menjadi **Three-Address Code (TAC)**, yaitu
instruksi sederhana yang umumnya hanya memuat satu operator dan paling banyak
tiga "alamat" (operand), berbentuk `x = y op z`.

Dua mekanisme kunci:

- **Variabel temporer** (`t1`, `t2`, ...) untuk menampung hasil sub-ekspresi.
- **Label** (`L1`, `L2`, ...) beserta `goto` / `ifFalse ... goto` untuk
  menerjemahkan alur perulangan.

Pola penerjemahan `while` adalah:

```
L1:                          # label awal perulangan
    <kode untuk kondisi>
    ifFalse <kondisi> goto L2   # jika kondisi salah, keluar dari loop
    <kode untuk body>
    goto L1                   # ulangi
L2:                          # label keluar
```

**Contoh keluaran TAC:**

```
 1: i = 0
 2: sum = 0
L1:
 4: t1 = i < 10
 5: ifFalse t1 goto L2
 6: t2 = i * 2
 7: t3 = sum + t2
 8: sum = t3
 9: t4 = i + 1
10: i = t4
11: goto L1
L2:
```

Penjelasan baris penting:
- Baris `t2 = i * 2` lalu `t3 = sum + t2` memperlihatkan ekspresi `sum + i * 2`
  dipecah sesuai presedensi (`*` dulu, baru `+`).
- `ifFalse t1 goto L2` keluar dari loop saat kondisi `i < 10` bernilai salah.
- `goto L1` mengembalikan eksekusi ke awal untuk iterasi berikutnya.

---

## 5. Cara Menjalankan Program

Prasyarat: **Python 3** sudah terpasang.

```bash
# 1) Menjalankan dengan contoh bawaan
python compiler.py

# 2) Menjalankan dengan file sumber sendiri
python compiler.py contoh.txt
```

Program akan menampilkan keempat tahap secara berurutan: daftar token, AST,
Symbol Table, dan Three-Address Code.

---

## 6. Penanganan Error

Program juga mendeteksi kesalahan pada setiap tahap dan menampilkan pesan yang jelas:

| Jenis Error | Contoh Masukan      | Pesan                                                       |
|-------------|---------------------|-------------------------------------------------------------|
| Leksikal    | `int a = 1 @ 2;`    | `[Leksikal] Karakter tidak dikenal '@' pada baris 1, kolom 11` |
| Sintaksis   | `int a = 1`         | `[Sintaksis] Mengharapkan 'SEMI' tetapi menemukan '<eof>'`  |
| Semantik    | `x = 5;`            | `[Semantik] Variabel 'x' dipakai sebelum dideklarasikan.`   |
| Semantik    | `int a=1; int a=2;` | `[Semantik] Variabel 'a' dideklarasikan ulang.`             |

---

## 7. Kesimpulan

Program ini berhasil menyimulasikan alur kerja sebuah *compiler* untuk konstruksi
perulangan `while`, mulai dari teks sumber hingga kode antara. Setiap tahap
(leksikal → sintaksis → semantik → generasi kode) memiliki tanggung jawab yang
jelas dan saling bergantung: keluaran satu tahap menjadi masukan tahap berikutnya.
Dengan demikian, tugas ini memperlihatkan pemahaman menyeluruh terhadap tahapan
utama dalam proses kompilasi.

---

## 8. Struktur Berkas

```
tugas-uas-teknik-kompilasi/
├── compiler.py      # implementasi mini-compiler (4 tahap kompilasi)
├── contoh.txt       # contoh program masukan
├── DOKUMENTASI.md   # dokumen penjelasan (berkas ini)
└── README.md        # ringkasan & cara menjalankan
```
