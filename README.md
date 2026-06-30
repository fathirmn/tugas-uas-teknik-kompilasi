# Tugas UAS Teknik Kompilasi — Representasi Tahapan Kompilasi

Mini-compiler dalam **Python 3** yang menyimulasikan **empat tahapan utama proses
kompilasi** untuk konstruksi perulangan **`while`**:

1. **Analisis Leksikal** — memecah source code menjadi *token*.
2. **Analisis Sintaksis** — membangun *Abstract Syntax Tree* (AST) dengan
   *Recursive Descent Parser*.
3. **Analisis Semantik** — pengecekan dasar memakai *Symbol Table*
   (variabel harus dideklarasikan, tipe cocok, tidak ada deklarasi ganda).
4. **Generasi Kode Antara** — menghasilkan *Three-Address Code* (TAC) lengkap
   dengan variabel temporer (`t1`, `t2`, …) dan label lompatan (`L1`, `L2`, …).

## Cara Menjalankan

Prasyarat: **Python 3** (tanpa library tambahan).

```bash
python compiler.py            # memakai contoh bawaan
python compiler.py contoh.txt # memakai file sumber sendiri
```

## Contoh Masukan

```c
int i = 0;
int sum = 0;
while (i < 10) {
    sum = sum + i * 2;
    i = i + 1;
}
```

## Contoh Keluaran (Three-Address Code)

```
i = 0
sum = 0
L1:
t1 = i < 10
ifFalse t1 goto L2
t2 = i * 2
t3 = sum + t2
sum = t3
t4 = i + 1
i = t4
goto L1
L2:
```

## Berkas

| Berkas            | Keterangan                                              |
|-------------------|---------------------------------------------------------|
| `compiler.py`     | Implementasi mini-compiler (4 tahap).                   |
| `contoh.txt`      | Contoh program masukan.                                 |
| `DOKUMENTASI.md`  | **Dokumen penjelasan lengkap** (grammar BNF + tiap tahap). |
| `README.md`       | Ringkasan ini.                                          |

> 📄 Penjelasan lengkap setiap tahapan ada di **[DOKUMENTASI.md](DOKUMENTASI.md)**.
