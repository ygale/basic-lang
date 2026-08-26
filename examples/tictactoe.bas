10 PRINT "Tic Tac Toe"
20 PRINT
30 PRINT " 1 | 2 | 3"
40 PRINT "---+---+---"
50 PRINT " 4 | 5 | 6"
60 PRINT "---+---+---"
70 PRINT " 7 | 8 | 9"
75 PRINT
80 REM Board: empty=0, X=1, O=4
90 DIM B[9]
95 DIM E[9]
100 REM |            |
110 REM | Load lines |
120 REM |            |
130 DIM L[8]
140 FOR I = 1 TO 8
150 READ L[I]
160 DATA 123, 456, 789, 147, 258, 369, 159, 357
170 NEXT I
180 REM |              |
190 REM | Load gambits |
200 REM |              |
210 DIM G[8]
220 FOR I = 1 TO 8
230 READ G[I]
240 DATA 12597, 13749, 14593, 15827, 16327, 17329, 18743
250 DATA 19327
260 NEXT I
300 REM |          |
310 REM | New game |
320 REM |          |
325 REM Initialize board
340 FOR I = 1 TO 9
350 LET B[I] = 0
360 NEXT I
370 LET M = 1
375 LET C = 0
500 REM |             |
510 REM | Make a move |
520 REM |             |
525 LET B[ABS(M)] = 1
530 LET C = C * 10 + ABS(M)
535 PRINT "My move:", ABS(M)
540 REM Print the board
545 PRINT
550 FOR I = 1 TO 9
560 REM Print space, X, or O
570 PRINT " "; CHR((283 - 59 * B[I]) * B[I] / 4 + 32);
580 IF I / 3 = INT(I / 3) THEN 610
590 PRINT " |";
600 GOTO 640
610 PRINT
620 IF I = 9 THEN 640
630 PRINT "---+---+---"
640 NEXT I
650 PRINT
660 IF M < 0 THEN 5000
670 IF C >= 111111111 THEN 5100
680 REM |                     |
690 REM | Get opponent's move |
700 REM |                     |
720 PRINT "Your move (1-9, or 0 to quit)";
730 INPUT A
740 IF A = 0 THEN 9999
745 LET A = INT(A)
750 IF ABS(A - 5) < 5 THEN 780
760 PRINT "Illegal move"
770 GOTO 720
780 IF B[A] = 0 THEN 820
790 PRINT "Square", CHR(48 + A), "is taken - it's an ";
800 PRINT CHR(91 - 3 * B[A]); "."
810 GOTO 720
820 LET B[A] = 4
830 LET C = C * 10 + A
840 REM |                 |
850 REM | Check for a win |
860 REM |                 |
870 LET R = 2
880 GOTO 3000
1000 REM |                    |
1010 REM | Check for a gambit |
1020 REM |                    |
1030 FOR I = 1 TO 8
1040 LET G1 = G[I]
1050 IF G1 <= C THEN 1200
1060 IF INT(G1 / 10) = C THEN 1100
1070 LET G1 = INT(G1 / 100)
1080 GOTO 1050
1100 LET M = G1 - INT(G1 / 10) * 10
1110 GOTO 500
1200 NEXT I
1210 REM |                   |
1220 REM | Check for a block |
1230 REM |                   |
1240 LET R = 8
1250 GOTO 3000
2000 REM |                               |
2010 REM | Move in a random empty square |
2020 REM |                               |
2030 LET N = 0
2040 FOR I = 1 TO 9
2050 IF B[I] > 0 THEN 2080
2060 LET N = N + 1
2070 LET E[N] = I
2080 NEXT I
2090 IF N < 1 THEN 5100
2100 LET M = E[INT(RND(0) * N) + 1]
2110 GOTO 500
3000 REM |                  |
3010 REM | Check for a line |
3020 REM |                  |
3030 FOR I = 1 TO 8
3040 LET S1 = INT(L[I] / 100)
3050 LET S2 = INT(L[I] / 10) - S1 * 10
3060 LET S3 = L[I] - S2 * 10 - S1 * 100
3070 IF B[S1] + B[S2] + B[S3] = R THEN 3110
3080 NEXT I
3090 IF R = 2 THEN 1000
3100 GOTO 2000
3110 REM Found a line. Move in the empty square.
3120 LET M = S1 * (1 - SGN(B[S1]))
3130 LET M = M + S2 * (1 - SGN(B[S2]))
3140 LET M = M + S3 * (1 - SGN(B[S3]))
3150 IF R <> 2 THEN 500
3160 LET M = -M
3170 GOTO 500
5000 PRINT "Tic Tac Toe! I win!"
5010 GOTO 5200
5100 PRINT "Cat's game."
5200 PRINT
5210 PRINT "Play again (0=no, 1=yes)";
5220 INPUT A
5230 IF A > 0 THEN 300
9999 END
