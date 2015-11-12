#/usr/bin/env python

#
# ChessBoard - a Python program to find the next move in chess
#
# Copyright (c)            John Eriksson - http://arainyday.se
# Copyright (c) 2010-2015  Doug Blank <doug.blank@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id: $

"""
Plays a random game of chess. Some abbreviations and terms:
  Uppercase: white, Lowercase: black
  r,R - rook
  b,B - bishop
  n,N - Knight
  k,K - King
  q,Q - queen
  p,P - pawn

  ep - "en passant", special pawn move
"""

from copy import deepcopy
import random

def printReason(game_result):
    # Reason values
    if game_result == 0:
        #print("Running...")
        pass
    elif game_result == 1:
        print("INVALID_MOVE")
    elif game_result == 2:
        print("INVALID_COLOR")
    elif game_result == 3:
        print("INVALID_FROM_LOCATION")
    elif game_result == 4:
        print("INVALID_TO_LOCATION")
    elif game_result == 5:
        print("MUST_SET_PROMOTION")
    elif game_result == 6:
        print("GAME_IS_OVER")
    elif game_result == 7:
        print("AMBIGUOUS_MOVE")
    # Result values
    elif game_result == 8:
        print("WHITE_WIN")
    elif game_result == 9:
        print("BLACK_WIN")
    elif game_result == 10:
        print("STALEMATE")
    elif game_result == 11:
        print("STASIS_COUNT_LIMIT_RULE")
    elif game_result == 12:
        print("THREE_REPETITION_RULE")

def makeRepr(state, board):
    b = ""
    for l in board:
        b += "%s%s%s%s%s%s%s%s" % (l[0],l[1],l[2],l[3],l[4],l[5],l[6],l[7])
    d = (b,
         state.player,
         state.white_king_castle,
         state.white_queen_castle,
         state.black_king_castle,
         state.black_queen_castle,
         state.ep[0],
         state.ep[1],
         state.game_result,
         state.stasis_count)
    #turn,wkc,wqc,bkc,bqc,epx,epy,game_result,stasis_count
    s = "%s%s%d%d%d%d%d%d%d:%d" % d
    return s

class State(object):
    """
    Container for move state.
    """
    def __init__(self, player):
        self.game_result = 0 
        self.reason = 0
        # States
        self.player = player
        self.white_king_castle = True
        self.white_queen_castle = True
        self.black_king_castle = True
        self.black_queen_castle = True
        #none or the location of the current en passant pawn:
        self.ep = [0, 0]      
        self.stasis_count = 0
        self.move_count = 0
        self.black_king_location = (0, 0)
        self.white_king_location = (0, 0)
        # three rep stack
        self.three_rep_stack = []
        # full state stack
        self.state_stack = []
        self.state_stack_pointer = 0
        # all moves, stored to make it easier to build textmoves
        #[piece,from,to,takes,promotion,check/checkmate,specialmove]
        #["KQRNBP",(fx,fy),(tx,ty),True/False,"QRNB"/None,"+#"/None,0-5]
        self.cur_move = [None,None,None,False,None,None,0]
        self.moves = []
        self.promotion_value = 1

    def setEP(self,epPos):
        self.ep[0], self.ep[1] = epPos
   
    def clearEP(self):
        self.ep[0] = 0
        self.ep[1] = 0

    def threeRepetitions(self):
        ts = self.three_rep_stack[:self.state_stack_pointer]
        if not len(ts):
            return False
        last = ts[len(ts)-1]
        if(ts.count(last) == 3):
            return True
        return False

    def endGame(self, reason):
        self.game_result = reason

    def pushState(self, board):
        if self.state_stack_pointer != len(self.state_stack):
            self.state_stack = self.state_stack[:self.state_stack_pointer]    
            self.three_rep_stack =  self.three_rep_stack[:self.state_stack_pointer]
            self.moves = self.moves[:self.state_stack_pointer-1]
        three_state = [self.white_king_castle,
                       self.white_queen_castle,
                       self.black_king_castle,
                       self.black_queen_castle,
                       deepcopy(board),
                       deepcopy(self.ep)]
        self.three_rep_stack.append(three_state)
        state_str = makeRepr(self, board)
        self.state_stack.append(state_str)
        self.state_stack_pointer = len(self.state_stack)            

    def pushMove(self):
        """
        Push the current move onto the moves stack.
        """
        self.moves.append(deepcopy(self.cur_move))
               
    def getMoveCount(self):
        """
        Returns the number of halfmoves in the stack. 
        Zero (0) means no moves has been made.
        """
        return len(self.state_stack)-1

    def getCurrentMove(self):
        """
        Returns the current halfmove number. Zero (0) means before
        first move.
        """
        return self.state_stack-1

    def setPromotion(self, promotion):
        """
        Tell the chessboard how to promote a pawn.
        1=QUEEN,2=ROOK,3=KNIGHT,4=BISHOP You can also set promotion to
        0 (zero) to reset the promotion value.
        """
        self.promotion_value = promotion

    def getPromotion(self):
        """
        Returns the current promotion value.
        1=QUEEN,2=ROOK,3=KNIGHT,4=BISHOP
        """
        return self.promotion_value

    def getLastMoveType(self, board):
        """
        Returns a value that indicates if the last move was a "special
        move".  Returns -1 if no move has been done.  Return value can
        be: 0=NORMAL_MOVE 1=EP_MOVE (Pawn is moved two steps and is
        valid for en passant strike) 2=EP_CAPTURE_MOVE (A pawn has
        captured another pawn by using the en passant rule)
        3=PROMOTION_MOVE (A pawn has been promoted. Use getPromotion()
        to see the promotion piece.)  4=KING_CASTLE_MOVE (Castling on
        the king side.)  5=QUEEN_CASTLE_MOVE (Castling on the queen
        side.)
        """
        if self.state_stack_pointer<=1: # No move has been done at thos pointer
            return -1
        self.undo(board)
        move = self.moves[self.state_stack_pointer-1]        
        res = move[6]
        self.redo(board)
        return res

    def getLastMove(self):
        """
        Returns a tupple containing two tupples describing the move
        just made using the internal coordinates.

        In the format ((from_x, from_y), (to_x, to_y))
        Ex. ((4, 6), (4, 4))
        Returns None if no moves has been made.
        """
        if self.state_stack_pointer<=1: # No move has been done at thos pointer
            return None
        self.undo(board)
        move = self.moves[self.state_stack_pointer-1]        
        res = (move[1], move[2])
        self.redo(board)
        return res

    def getAllMoves(self, board, format=1):
        """
        Returns a list of all moves done so far in Algebraic chess notation.
        Returns None if no moves has been made.
        """
        if self.state_stack_pointer<=1: # No move has been done at this pointer
            return None
        res = []
        point = self.state_stack_pointer
        self.gotoFirst(board)
        while True:
            move = self.moves[self.state_stack_pointer-1]  
            res.append(self.formatTextMove(move, format))
            if self.state_stack_pointer >= len(self.state_stack)-1:
                break
            self.redo(board)
        self.state_stack_pointer = point
        self.loadCurState(board)
        return res

    def getLastMove(self, board, format=1):
        """
        Returns the latest move as Algebraic chess notation.
        Returns None if no moves has been made.
        """
        if self.state_stack_pointer<=1: # No move has been done at that pointer
            return None
        self.undo(board)
        move = self.moves[self.state_stack_pointer-1]        
        res = self.formatTextMove(move, format)
        self.redo(board)
        return res
         
    def gotoMove(self, board, move):
        """
        Goto the specified halfmove. Zero (0) is before the first move.
        Return False if move is out of range.
        """
        move+=1
        if move > len(self.state_stack):
            return False
        if move < 1:
            return False
        self.state_stack_pointer = move
        self.loadCurState(board)
                          
    def loadCurState(self, board):
        s = self.state_stack[self.state_stack_pointer-1]
        b= s[:64]
        v = s[64:72]
        f =  int(s[73:])
        idx = 0
        for r in range(8):
            for c in range(8):
                board[r][c]=b[idx]
                idx+=1
        self.player                = v[0]
        self.white_king_castle     = int(v[1])
        self.white_queen_castle    = int(v[2]) 
        self.black_king_castle     = int(v[3])
        self.black_queen_castle    = int(v[4])
        self.ep[0]                 = int(v[5])
        self.ep[1]                 = int(v[6])
        self.game_result           = int(v[7])
        self.stasis_count = f
                        
    def gotoFirst(self, board):
        """
        Goto before the first known move.
        """
        self.state_stack_pointer = 1
        self.loadCurState(board)

    def gotoLast(self, board):
        """
        Goto after the last knwon move.
        """
        self.state_stack_pointer = len(self.state_stack)
        self.loadCurState(board)
        
    def undo(self, board):
        """
        Undo the last move. Can be used to step back until the initial
        board setup.
        Returns True or False if no more moves can be undone.
        """
        if self.state_stack_pointer <= 1:
            return False
        self.state_stack_pointer -= 1
        self.loadCurState(board)
        return True

    def redo(self, board):
        """
        If you used the undo method to step backwards you can use this
        method to step forward until the last move i reached.  Returns
        True or False if no more moves can be redone.
        """
        if self.state_stack_pointer == len(self.state_stack):
            return False
        self.state_stack_pointer += 1
        self.loadCurState(board)
        return True

class ChessBoard(object):
    """
    The class that holds the board and values.
    """
    # Promotion values
    QUEEN = 1
    ROOK = 2
    KNIGHT = 3
    BISHOP = 4
    # Reason values
    INVALID_MOVE = 1
    INVALID_COLOR = 2
    INVALID_FROM_LOCATION = 3
    INVALID_TO_LOCATION = 4
    MUST_SET_PROMOTION = 5
    GAME_IS_OVER = 6
    AMBIGUOUS_MOVE = 7
    # Result values
    WHITE_WIN = 8
    BLACK_WIN = 9
    STALEMATE = 10
    STASIS_COUNT_LIMIT_RULE = 11
    THREE_REPETITION_RULE = 12
    # Special moves
    NORMAL_MOVE = 0
    EP_MOVE = 1
    EP_CAPTURE_MOVE = 2
    PROMOTION_MOVE = 3
    KING_CASTLE_MOVE = 4
    QUEEN_CASTLE_MOVE = 5
    # Text move output type
    AN = 0      # g4-e3
    SAN = 1     # Bxe3
    LAN = 2     # Bg4xe3

    def __init__(self):
        self.resetBoard()

    def __repr__(self):
        """
        Return the current board layout.
        """
        s =  "  lower = b upper = W\n"
        s += "  +-----------------+\n"
        rank = 8
        i = 0
        for l in self.board:
            s += "%d | %s %s %s %s %s %s %s %s | %d\n" % (
                rank, l[0], l[1], l[2], l[3], 
                l[4], l[5], l[6], l[7], i)
            rank-=1
            i += 1
        s += "  +-----------------+\n"
        s += "    A B C D E F G H\n"  
        s += "    0 1 2 3 4 5 6 7\n"  
        return s

    def getOtherPlayer(self, state):
        if state.player == 'w':
            return 'b'
        elif state.player == 'b':
            return 'w'
        else:
            raise AttributeException("invalid player: '%s'" % state.player)

    def checkKingGuard(self, state, fromPos, moves, specialMoves={}):
        result = []
        kx, ky = self.getKingLocation(state)
        fx, fy = fromPos
        done = False
        fp = self.board[fy][fx]
        self.board[fy][fx] = " "
        if not self.isThreatened(state, kx, ky):
            done = True
        self.board[fy][fx] = fp
        if done:
            return moves
        for m in moves:
            tx, ty = m
            sp = None
            fp = self.board[fy][fx]
            tp = self.board[ty][tx]
            self.board[fy][fx] = " "
            self.board[ty][tx] = fp
            if ((m in specialMoves) and 
                specialMoves[m] == self.EP_CAPTURE_MOVE):
                sp = self.board[state.ep[1]][state.ep[0]]
                self.board[state.ep[1]][state.ep[0]] = " "
            if not self.isThreatened(state, kx, ky):
                result.append(m)
            if sp:
                self.board[state.ep[1]][state.ep[0]] = sp
            self.board[fy][fx] = fp
            self.board[ty][tx] = tp
        return result    
       
    def isFree(self, x, y):
        """
        Is this spot on the board open?
        """
        return self.board[y][x] == ' ' 

    def getColor(self, x, y):
        """
        Get the color of the spot on the board.
        Returns ' ', 'w', or 'b'.
        """
        if self.board[y][x] == ' ':
            return ' '
        elif self.board[y][x].isupper():
            return 'w'
        elif self.board[y][x].islower():
            return 'b'
                
    def isThreatened(self, state, lx, ly):
        if state.player == 'w':
            if lx<7 and ly>0 and self.board[ly-1][lx+1] == 'p':
                return True
            elif lx>0 and ly>0 and self.board[ly-1][lx-1] == 'p':
                return True
        else:  
            if lx<7 and ly<7 and self.board[ly+1][lx+1] == 'P':
                return True
            elif lx>0 and ly<7 and self.board[ly+1][lx-1] == 'P':
                return True
        m =[(lx+1, ly+2), (lx+2, ly+1), (lx+2, ly-1), (lx+1, ly-2), 
            (lx-1, ly+2), (lx-2, ly+1), (lx-1, ly-2), (lx-2, ly-1)]
        for p in m:
            if p[0] >= 0 and p[0] <= 7 and p[1] >= 0 and p[1] <= 7: 
                if self.board[p[1]][p[0]] == "n" and state.player=='w':
                    return True                
                elif self.board[p[1]][p[0]] == "N" and state.player=='b':
                    return True
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), 
                (1, 1), (-1, 1), (1, -1), (-1, -1)]        
        for d in dirs:
            x = lx 
            y = ly
            dx, dy = d
            steps = 0
            while True:
                steps+=1
                x+=dx
                y+=dy
                if x<0 or x>7 or y<0 or y>7:
                    break
                if self.isFree(x, y):
                    continue
                elif self.getColor(x, y)==state.player:
                    break
                else:
                    p = self.board[y][x].upper()
                    if p == 'K' and steps == 1:
                        return True
                    elif p == 'Q':
                        return True
                    elif p == 'R' and abs(dx) != abs(dy):
                        return True
                    elif p == 'B' and abs(dx) == abs(dy):
                        return True 
                    break
        return False

    def hasAnyValidMoves(self, state):
        """
        Does the state.player have any valid moves?
        """
        for y in range(0, 8):
            for x in range(0, 8):
                if self.getColor(x, y) == state.player:
                    if len(self.getValidMoves(state, (x, y))):
                        return True
        return False

    #-----------------------------------------------------------------
    def traceValidMoves(self, state, fromPos, dirs, maxSteps=8):
        """
        How far can a piece move fromPos in the directions in dirs
        before running off the board, or running into another piece?
        """
        moves = []
        for d in dirs:
            x, y = fromPos
            dx, dy = d
            steps = 0
            while True:
                x+=dx
                y+=dy
                if x<0 or x>7 or y<0 or y>7:
                    break
                if self.isFree(x, y):
                    moves.append((x, y))
                elif self.getColor(x, y) != state.player:
                    moves.append((x, y))
                    break
                else:
                    break
                steps += 1
                if steps == maxSteps:
                    break
        return moves
    
    def getValidQueenMoves(self, state, fromPos):
        """
        Return all of the valid moves that the queen can make.
        """
        moves = []        
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), 
                (1, 1), (-1, 1), (1, -1), (-1, -1)]
        moves = self.traceValidMoves(state, fromPos, dirs)
        moves = self.checkKingGuard(state, fromPos, moves)
        return moves        

    def getValidRookMoves(self, state, fromPos):
        """
        Return all of the valid moves that the rook can make.
        """
        moves = []        
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        moves = self.traceValidMoves(state, fromPos, dirs)
        moves = self.checkKingGuard(state, fromPos, moves)
        return moves        

    def getValidBishopMoves(self, state, fromPos):
        """
        Return all of the valid moves that the bishop can make.
        """
        moves = []
        dirs = [(1, 1), (-1, 1), (1, -1), (-1, -1) ]
        moves = self.traceValidMoves(state, fromPos, dirs)
        moves = self.checkKingGuard(state, fromPos, moves)
        return moves        
                    
    def getValidPawnMoves(self, state, fromPos):
        """
        Return all of the valid moves that the pawn can make.
        Handles special moves, such en passant.
        """
        moves = []
        specialMoves = {}
        fx, fy = fromPos
        if state.player == 'w':
            movedir = -1
            startrow = 6
            ocol = 'b'
            eprow = 3
        else:
            movedir = 1
            startrow = 1
            ocol = 'w'
            eprow = 4
        if self.isFree(fx, fy+movedir):
            moves.append((fx, fy+movedir))
        if fy == startrow:
            if self.isFree(fx, fy+movedir) and self.isFree(fx, fy+(movedir*2)):
                moves.append((fx, fy+(movedir*2)))
                specialMoves[(fx, fy+(movedir*2))] = self.EP_MOVE
        if fx < 7 and self.getColor(fx+1, fy+movedir) == ocol:
            moves.append((fx+1, fy+movedir))
        if fx > 0 and self.getColor(fx-1, fy+movedir) == ocol:
            moves.append((fx-1, fy+movedir))
        if fy == eprow and state.ep[1] != 0:
            if state.ep[0] == fx+1:
               moves.append((fx+1, fy+movedir))
               specialMoves[(fx+1, fy+movedir)] = self.EP_CAPTURE_MOVE
            if state.ep[0] == fx-1:
               moves.append((fx-1, fy+movedir))
               specialMoves[(fx-1, fy+movedir)] = self.EP_CAPTURE_MOVE
        moves = self.checkKingGuard(state, fromPos, moves, specialMoves)
        return (moves, specialMoves)

    def getValidKnightMoves(self, state, fromPos):
        """
        Return all of the valid moves that the knight can make.
        """
        moves = []
        fx, fy = fromPos
        m =[(fx+1, fy+2), (fx+2, fy+1), (fx+2, fy-1), (fx+1, fy-2), 
            (fx-1, fy+2), (fx-2, fy+1), (fx-1, fy-2), (fx-2, fy-1)]
        for p in m:
            if p[0] >= 0 and p[0] <= 7 and p[1] >= 0 and p[1] <= 7: 
                if self.getColor(p[0], p[1])!=state.player:
                    moves.append(p)
        moves = self.checkKingGuard(state, fromPos, moves)
        return moves    
            
    def getValidKingMoves(self, state, fromPos):
        """
        Return all of the valid moves that the king can make.
        """
        moves = []
        specialMoves={}
        if state.player == 'w':
            c_row = 7
            c_king = state.white_king_castle
            c_queen = state.white_queen_castle
            k = "K"
        else:
            c_row = 0
            c_king = state.black_king_castle
            c_queen = state.black_queen_castle
            k = "k"
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), 
                (1, 1), (-1, 1), (1, -1), (-1, -1) ]
        t_moves = self.traceValidMoves(state, fromPos, dirs, 1)
        moves = []
        self.board[fromPos[1]][fromPos[0]] = ' '
        for m in t_moves:
            if not self.isThreatened(state, m[0], m[1]):
                moves.append(m)
        if c_king: 
            if (self.isFree(5, c_row) and self.isFree(6, c_row) and 
                self.board[c_row][7].upper() == 'R'):   
                if (not self.isThreatened(state, 4, c_row) and 
                    not self.isThreatened(state, 5, c_row) and 
                    not self.isThreatened(state, 6, c_row)):   
                    moves.append((6, c_row))
                    specialMoves[(6, c_row)] = self.KING_CASTLE_MOVE
        if c_queen: 
            if (self.isFree(3, c_row) and self.isFree(2, c_row) and 
                self.isFree(1, c_row) and self.board[c_row][0].upper() == 'R'): 
                if (not self.isThreatened(state, 4, c_row) and 
                    not self.isThreatened(state, 3, c_row) and 
                    not self.isThreatened(state, 2, c_row)): 
                    moves.append((2, c_row))
                    specialMoves[(2, c_row)] = self.QUEEN_CASTLE_MOVE
        self.board[fromPos[1]][fromPos[0]] = k
        return (moves, specialMoves)        

    # -----------------------------------------------------
    def movePawn(self, state, fromPos, toPos):
        moves, specialMoves = self.getValidPawnMoves(state, fromPos)
        if not toPos in moves:
            return False
        if toPos in specialMoves:
            t = specialMoves[toPos]
        else:
            t = 0
        if t == self.EP_CAPTURE_MOVE:
            self.board[state.ep[1]][state.ep[0]] = ' '
            state.cur_move[3]=True
            state.cur_move[6]=self.EP_CAPTURE_MOVE
        pv = state.promotion_value
        if state.player == 'w' and toPos[1] == 0:
            if pv == 0:
                state.reason = self.MUST_SET_PROMOTION
                return False
            pc = ['Q', 'R', 'N', 'B']
            p = pc[pv-1]
            state.cur_move[4]=p
            state.cur_move[6]=self.PROMOTION_MOVE
            #state.promotion_value = 0
        elif state.player == 'b' and toPos[1] == 7:
            if pv == 0:
                state.reason = self.MUST_SET_PROMOTION
                return False
            pc = ['q', 'r', 'n', 'b']
            p = pc[pv-1]
            state.cur_move[4]=p
            state.cur_move[6]=self.PROMOTION_MOVE
            #state.promotion_value = 0
        else:
            p = self.board[fromPos[1]][fromPos[0]]
        if t == self.EP_MOVE:
            state.setEP(toPos)
            state.cur_move[6]=self.EP_MOVE
        else:
            state.clearEP()
        if self.board[toPos[1]][toPos[0]] != ' ':
            state.cur_move[3]=True
        self.board[toPos[1]][toPos[0]] = p
        self.board[fromPos[1]][fromPos[0]] = " "
        state.stasis_count = 0
        return True

    def moveKnight(self, state, fromPos, toPos):
        moves = self.getValidKnightMoves(state, fromPos)
        if not toPos in moves:
            return False
        state.clearEP()
        if self.board[toPos[1]][toPos[0]] == " ":   
            state.stasis_count+=1
        else:
            state.stasis_count=0
            state.cur_move[3]=True
        self.board[toPos[1]][toPos[0]] = self.board[fromPos[1]][fromPos[0]]
        self.board[fromPos[1]][fromPos[0]] = " "     
        return True

    def moveKing(self, state, fromPos, toPos):
        if state.player == 'w':
            c_row = 7
            k = "K"
            r = "R"
        else:
            c_row = 0
            k = "k"
            r = "r"
        moves, specialMoves = self.getValidKingMoves(state, fromPos)
        if toPos in specialMoves:
            t = specialMoves[toPos]
        else:
            t = 0
        if not toPos in moves:
            return False
        state.clearEP()
        if state.player == 'w':
            state.white_king_castle = False
            state.white_queen_castle = False
        else:
            state.black_king_castle = False
            state.black_queen_castle = False
        if t == self.KING_CASTLE_MOVE:
            state.stasis_count+=1
            self.board[c_row][4] = " "
            self.board[c_row][6] = k     
            self.board[c_row][7] = " "
            self.board[c_row][5] = r
            state.cur_move[6] = self.KING_CASTLE_MOVE
        elif t == self.QUEEN_CASTLE_MOVE:
            state.stasis_count+=1
            self.board[c_row][4] = " "
            self.board[c_row][2] = k
            self.board[c_row][0] = " "
            self.board[c_row][3] = r     
            state.cur_move[6] = self.QUEEN_CASTLE_MOVE
        else:                      
            if self.board[toPos[1]][toPos[0]] == " ":     
                state.stasis_count+=1
            else:
                state.stasis_count=0
                state.cur_move[3]=True
            self.board[toPos[1]][toPos[0]] = self.board[fromPos[1]][fromPos[0]]
            self.board[fromPos[1]][fromPos[0]] = " "
        return True

    def moveQueen(self, state, fromPos, toPos):
        moves = self.getValidQueenMoves(state, fromPos)
        if not toPos in moves:
            return False
        state.clearEP()
        if self.board[toPos[1]][toPos[0]] == " ":    
            state.stasis_count+=1
        else:
            state.stasis_count=0
            state.cur_move[3]=True
        self.board[toPos[1]][toPos[0]] = self.board[fromPos[1]][fromPos[0]]
        self.board[fromPos[1]][fromPos[0]] = " "     
        return True

    def moveBishop(self, state, fromPos, toPos):
        moves = self.getValidBishopMoves(state, fromPos)
        if not toPos in moves:
            return False
        state.clearEP()
        if self.board[toPos[1]][toPos[0]] == " ":
            state.stasis_count+=1
        else:
            state.stasis_count=0
            state.cur_move[3]=True
        self.board[toPos[1]][toPos[0]] = self.board[fromPos[1]][fromPos[0]]
        self.board[fromPos[1]][fromPos[0]] = " "     
        return True

    def moveRook(self, state, fromPos, toPos):
        moves = self.getValidRookMoves(state, fromPos)
        if not toPos in moves:
            return False
        fx, fy = fromPos
        if state.player == 'w':
            if fx == 0:
                state.white_queen_castle = False
            if fx == 7:
                state.white_king_castle = False
        elif state.player == 'b':
            if fx == 0:
                state.black_queen_castle = False
            if fx == 7:
                state.black_king_castle = False
        state.clearEP()
        if self.board[toPos[1]][toPos[0]] == " ":    
            state.stasis_count+=1
        else:
            state.stasis_count=0
            state.cur_move[3]=True
        self.board[toPos[1]][toPos[0]] = self.board[fromPos[1]][fromPos[0]]
        self.board[fromPos[1]][fromPos[0]] = " "     
        return True

    def parseTextMove(self, state, txt):
        """
        Makes a move from a state, and a standard chess text format.
        Examples: "O-O", "g4-e3", "Bxe3", "Bg4xe3", etc.
        Returns (h_piece, h_file, h_rank, dest_x, dest_y, promotion)
        """
        txt = txt.strip()
        promotion = None
        dest_x = 0
        dest_y = 0
        h_piece = "P"
        h_rank = -1
        h_file = -1
        # handle the special 
        if txt == "O-O":
            if state.player == 'w':
                return (None, 4, 7, 6, 7, None)
            if state.player == 'b':
                return (None, 4, 0, 6, 0, None)
        if txt == "O-O-O":
            if state.player == 'w':
                return (None, 4, 7, 2, 7, None)
            if state.player == 'b':
                return (None, 4, 0, 2, 0, None)
        files = {"a":0, "b":1, "c":2, "d":3, "e":4, "f":5, "g":6, "h":7}
        ranks = {"8":0, "7":1, "6":2, "5":3, "4":4, "3":5, "2":6, "1":7}
        # Clean up the textmove
        "".join(txt.split("e.p."))
        t = []
        for ch in txt:
            if ch not in "KQRNBabcdefgh12345678":
                continue    
            t.append(ch)
        if len(t)<2:
            return None
        # Get promotion if any
        if t[-1] in ('Q', 'R', 'N', 'B'):
            promotion = {'Q':1, 'R':2, 'N':3, 'B':4}[t.pop()]
        if len(t)<2:
            return None
        # Get the destination
        if not (t[-2] in files) or not (t[-1] in ranks):
            return None
        dest_x = files[t[-2]]
        dest_y = ranks[t[-1]]
        # Pick out the hints    
        t = t[:-2]  
        for h in t:
            if h in ('K', 'Q', 'R', 'N', 'B', 'P'):  
                h_piece = h
            elif h in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'):
                h_file = files[h]
            elif h in ('1', '2', '3', '4', '5', '6', '7', '8'):
                h_rank = ranks[h]
        # If we have both a source and destination we don't need the piece hint.
        # This will make us make the move directly.
        if h_rank > -1 and h_file > -1:
            h_piece = None
        return (h_piece, h_file, h_rank, dest_x, dest_y, promotion)

    def formatTextMove(self, move, format):
        """
        Creates standard chess text format from a move, and a format code
        (AN, LAN, or SAN).
        A move is "piece fromPos toPos take promotion check special"
        Format can be in AN, LAN, or SAN.
        """
        #piece, from, to, take, promotion, check, special
        piece = move[0]       # char code
        fpos = tuple(move[1]) # 2 ints, 0-7
        tpos = tuple(move[2]) # 2 ints, 0-7
        take = move[3]        # 0,1, true/false
        promo = move[4]       # 0/1, true/false
        check = move[5]       # 0/1, true/false
        special = move[6]     # code, 0 or KING_CASTLE_MOVE, etc
        files = "abcdefgh"
        ranks = "87654321"
        if format == self.AN:
            res = "%s%s%s%s" % (files[fpos[0]], ranks[fpos[1]], 
                                files[tpos[0]], ranks[tpos[1]])
        elif format == self.LAN:
            if special == self.KING_CASTLE_MOVE:
                return "O-O"
            elif special == self.QUEEN_CASTLE_MOVE:
                return "O-O-O"
            tc = "-"
            if take:
                tc = "x"
            pt = ""
            if promo:
                pt = "=%s" % promo
            if piece == "P":
                piece = ""
            if not check:
                check = ""
            res = "%s%s%s%s%s%s%s%s" % (piece, files[fpos[0]], ranks[fpos[1]], 
                                        tc,    files[tpos[0]], ranks[tpos[1]], 
                                        pt, check)
        elif format == self.SAN:
            if special == self.KING_CASTLE_MOVE:
                return "O-O"
            elif special == self.QUEEN_CASTLE_MOVE:
                return "O-O-O"
            tc = ""
            if take:
                tc = "x"
            pt = ""
            if promo:
                pt = "=%s" % promo.upper()
            p = piece
            if state.player == 'b':
                p = p.lower()
            if piece == "P":
                piece = ""
            if not check:
                check = ""
            fx, fy = fpos
            hint_f = ""
            hint_r = ""
            for y in range(8):
                for x in range(8):                    
                    if self.board[y][x] == p:
                        if x == fx and y == fy:
                            continue
                        vm = self.getValidMoves(state, (x, y))
                        if tpos in vm:
                            if fx == x:
                                hint_r = ranks[fy]
                            else:
                                hint_f = files[fx]
            if piece == "" and take:
                hint_f = files[fx]
            res = "%s%s%s%s%s%s%s%s" % (piece, hint_f, hint_r, tc, 
                                        files[tpos[0]], ranks[tpos[1]], 
                                        pt, check)
        return res

    def getValidMoves(self, state, location):
        """
        Returns a list of valid moves. (ex [ [3, 4], [3, 5], [3, 6]
        ... ] ) If there isn't a valid piece on that location or the
        piece on the selected location hasn't got any valid moves an
        empty list is returned.  The location argument must be a tuple
        containing an x, y value Ex. (3, 3)
        """
        if state.game_result:
            return []
        x, y = location
        if x < 0 or x > 7 or y < 0 or y > 7:
            return False
        if self.getColor(x, y) != state.player:
            return []
        p = self.board[y][x].upper()
        if p == 'P':
            m, s = self.getValidPawnMoves(state, location)
            return m
        elif p == 'R':
            return self.getValidRookMoves(state, location)
        elif p == 'B':
            return self.getValidBishopMoves(state, location)
        elif p == 'Q':
            return self.getValidQueenMoves(state, location)
        elif p == 'K':
            m, s = self.getValidKingMoves(state, location)
            return m
        elif p == 'N':
            return self.getValidKnightMoves(state, location)
        else:
            return []

    #-----------------------------------------------------------------------    
    # PUBLIC METHODS
    #-----------------------------------------------------------------------
    
    def getMoves(self, state):
        retval = []
        for y in range(0, 8):
            for x in range(0, 8):
                if self.getColor(x, y) == state.player:
                    moves = self.getMoveFrom(state, (x, y))
                    if moves:
                        retval.append(((x,y), self.board[y][x], moves))
        return retval
             
    def getMoveFrom(self, state, location):
        """
        Returns a list of valid moves. (ex [ [3, 4], [3, 5], [3, 6]
        ... ] ) If there isn't a valid piece on that location or the
        piece on the selected location hasn't got any valid moves an
        empty list is returned.  The location argument must be a tuple
        containing an x, y value Ex. (3, 3)
        """
        x, y = location
        if x < 0 or x > 7 or y < 0 or y > 7:
            return False
        p = self.board[y][x]
        p = p.upper()
        if p == 'P':
            m, s = self.getValidPawnMoves(state, location)
            return m
        elif p == 'R':
            return self.getValidRookMoves(state, location)
        elif p == 'B':
            return self.getValidBishopMoves(state, location)
        elif p == 'Q':
            return self.getValidQueenMoves(state, location)
        elif p == 'K':
            m, s = self.getValidKingMoves(state, location)
            return m
        elif p == 'N':
            return self.getValidKnightMoves(state, location)
        else:
            return []
        
    def resetBoard(self):
        """
        Resets the chess board and all states.
        """
        self.board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'], 
            ['p']*8, 
            [' ']*8, 
            [' ']*8, 
            [' ']*8, 
            [' ']*8, 
            ['P']*8, 
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
            ]

    def getKingLocation(self, state):
        for y in range(0,8):
            for x in range(0,8):
                if self.board[y][x] == "K" and state.player == 'w':
                    return (x,y)
                if self.board[y][x] == "k" and state.player == 'b':
                    return (x,y)

    def isCheck(self, state):
        """
        Returns True if the current players king is checked.
        """            
        kx, ky = self.getKingLocation(state)
        return self.isThreatened(state, kx, ky)
             
    def getBoard(self):
        """
        Returns a copy of the current board layout. Uppercase letters
        for white, lowercase for black.  K=King, Q=Queen, B=Bishop,
        N=Night, R=Rook, P=Pawn.  Empty squares are markt with a
        period (.)
        """
        return deepcopy(self.board)        

    def makeMove(self, state, fromPos, toPos):
        """
        Tries to move the piece located om fromPos to toPos. Returns
        True if that was a valid move.  The position arguments must be
        tuples containing x, y value Ex. (4, 6).  This method also
        detects game over.
        
        If this method returns False. You can use the getReason method
        to determin why.
        """        
        fx, fy = fromPos
        tx, ty = toPos
        state.cur_move[1]=fromPos        
        state.cur_move[2]=toPos
        #check invalid coordinates
        if fx < 0 or fx > 7 or fy < 0 or fy > 7:
            state.reason = self.INVALID_FROM_LOCATION
            return False
        #check invalid coordinates
        if tx < 0 or tx > 7 or ty < 0 or ty > 7:    
            state.reason = self.INVALID_TO_LOCATION
            return False
        #check if any move at all
        if fx==tx and fy==ty:
            state.reason = self.INVALID_TO_LOCATION
            return False
        #check if piece on location
        if self.isFree(fx, fy):
            state.reason = self.INVALID_FROM_LOCATION
            return False
        #check color of piece
        if self.getColor(fx, fy) != state.player:
            state.reason = self.INVALID_COLOR
            return False
        # Call the correct handler
        p = self.board[fy][fx].upper()
        state.cur_move[0]=p        
        if p == 'P':
            if not self.movePawn(state, (fx, fy), (tx, ty)):
                if not state.reason:
                    state.reason = self.INVALID_MOVE
                return False
        elif p == 'R':
            if not self.moveRook(state, (fx, fy), (tx, ty)):
                state.reason = self.INVALID_MOVE
                return False
        elif p == 'B':
            if not self.moveBishop(state, (fx, fy), (tx, ty)):
                state.reason = self.INVALID_MOVE
                return False
        elif p == 'Q':
            if not self.moveQueen(state, (fx, fy), (tx, ty)):
                state.reason = self.INVALID_MOVE
                return False
        elif p == 'K':
            if not self.moveKing(state, (fx, fy), (tx, ty)):
                state.reason = self.INVALID_MOVE
                return False
        elif p == 'N':
            if not self.moveKnight(state, (fx, fy), (tx, ty)):
                state.reason = self.INVALID_MOVE
                return False
        else:
            return False
        state.pushState(self.board)
        state.pushMove()
        other = self.getOtherPlayerState(state)
        state.move_count += 1
        return True 

    def getOtherPlayerState(self, state):
        newState = deepcopy(state)
        if state.player == 'w':
            newState.player = 'b'
        else:
            newState.player = 'w'
        return newState

    def checkStatus(self, state):
        #print("Move: %s" % state.move_count)
        #print(self)
        if self.isCheck(state):
            state.cur_move[5]="+"
        if not self.hasAnyValidMoves(state):
            if self.isCheck(state):
                state.cur_move[5]="#"
                if state.player == 'w':
                    state.endGame(self.BLACK_WIN)
                else:            
                    state.endGame(self.WHITE_WIN)
            else:  
                state.endGame(self.STALEMATE)     
        else:
            if state.stasis_count == 100:
                state.endGame(self.STASIS_COUNT_LIMIT_RULE)
            elif state.threeRepetitions():
                state.endGame(self.THREE_REPETITION_RULE)
        printReason(state.game_result)

def makeWindow(size):
    window = Graphics.Window("Chess", size, size)
    for x in range(8):
        for y in range(8):
            r = Graphics.Rectangle((x * size/8, y * size/8),
                                   ((x + 1) * size/8, (y + 1) * size/8))
            if ((x % 2 == 0 and y % 2 == 0) or
                (x % 2 == 1 and y % 2 == 1)):
                r.color = Graphics.Color("white")
            else:
                r.color = Graphics.Color("gray")
            r.draw(window)
    for x in range(8):
        line = Graphics.Line((x * size/8, 0), (x * size/8, size))
        line.draw(window)
    for y in range(8):
        line = Graphics.Line((0, y * size/8), (size, y * size/8))
        line.draw(window)
    images = {}
    for x,w,piece in ((0,70,"king"), (140,80,"queen"), (300,60,"rook"),
                      (440,514-440,"bishop"), (590,662-590,"knight"), (750,50,"pawn")):
        for y,color in ((0, "black"), (125, "white")):
            images[(piece, color)] = (x, y, w, 80)
    return window, images

#chess_set = Graphics.Picture(calico.relativePath("../examples/images/chess_set.png"))

def displayBoard(window, board, images, count):
    size = window.width
    #chess_set = Graphics.Picture("/usr/local/lib/Calico/examples/images/chess_set.png")
    map = {"r": ("rook", "black"),
           "n": ("knight", "black"),
           "b": ("bishop", "black"),
           "q": ("queen", "black"),
           "k": ("king", "black"),
           "p": ("pawn", "black"),
           "R": ("rook", "white"),
           "N": ("knight", "white"),
           "B": ("bishop", "white"),
           "Q": ("queen", "white"),
           "K": ("king", "white"),
           "P": ("pawn", "white")}
    even = (count % 2) == 0
    for col in range(8):
        for row in range(8):
            if board.board[row][col] != ' ':
                x, y, w, h = images[map[board.board[row][col]]]
                image = chess_set.getRegion((x, y), w, h)
                if even:
                    image.tag = "piece-even"
                else:
                    image.tag = "piece-odd"
                image.border = 0
                image.x = (col * size/8) + (size/8)/2
                image.y = (row * size/8) + (size/8)/2
                image.draw(window)
    if even:
        window.removeTagged("piece-odd")
    else:
        window.removeTagged("piece-even")

def gplay(player1, player2):
    # player1 is black
    # player2 is white
    state = State('w')
    board = ChessBoard()
    size = 600
    window, images = makeWindow(size)
    window.title = "Chess: %s (black) vs %s (white)" % (player1.__name__, player2.__name__)
    count = 0
    displayBoard(window, board, images, count)
    while state.game_result == 0:
        count += 1
        moves = board.getMoves(state)
        if moves:
            if state.player == 'w':
                fromPos, toPos = player2(board, state, moves)
            else:
                fromPos, toPos = player1(board, state, moves)

            #print("%s moves %s from %s to %s" %
            #      (state.player, board.board[fromPos[1]][fromPos[0]],
            #       fromPos, toPos))
            rect1 = Graphics.Rectangle((fromPos[0] * size/8, fromPos[1] * size/8),
                                      ((fromPos[0] + 1) * size/8, (fromPos[1] + 1) * size/8))
            rect2 = Graphics.Rectangle((toPos[0] * size/8, toPos[1] * size/8),
                                      ((toPos[0] + 1) * size/8, (toPos[1] + 1) * size/8))
            even = (count % 2) == 0
            if even:
                rect1.tag = "piece-even"
                rect2.tag = "piece-even"
                rect1.fill = Graphics.Color("lightblue")
                rect2.fill = Graphics.Color("lightblue")
            else:
                rect1.tag = "piece-odd"
                rect2.tag = "piece-odd"
                rect1.fill = Graphics.Color("pink")
                rect2.fill = Graphics.Color("pink")
            rect1.draw(window)
            rect2.draw(window)
            board.makeMove(state, fromPos, toPos)
            displayBoard(window, board, images, count)
            if state.game_result == 0:
                state.player = board.getOtherPlayer(state)
                board.checkStatus(state)
        else:
            print("No moves!")
            break
    return state.game_result

def play(player1, player2):
    # player1 is black
    # player2 is white
    state = State('w')
    board = ChessBoard()
    print(board)
    while state.game_result == 0:
        moves = board.getMoves(state)
        if moves:
            if state.player == 'w':
                fromPos, toPos = player2(board, state, moves)
            else:
                fromPos, toPos = player1(board, state, moves)

            print("%s moves %s from %s to %s" %
                  (state.player, board.board[fromPos[1]][fromPos[0]],
                   fromPos, toPos))
            board.makeMove(state, fromPos, toPos)
            if state.game_result == 0:
                state.player = board.getOtherPlayer(state)
                board.checkStatus(state)
        else:
            print("No moves!")
            break
    return state.game_result

def randomPlayer1(board, state, moves):
    """
    This is a bad random player... first it picks a
    piece, then selects from one of its moves. This
    does not give ever move an equal chance of being
    picked.
    """
    # moves is a list of [(from, piece, moves), ...]
    # [((0, 1), 'P', [(0, 2), (0, 3)]), ...]
    selection = random.choice(moves)
    fromPos = selection[0]
    toPos = random.choice(selection[2])
    return fromPos, toPos

def randomPlayer2(board, state, moves):
    """
    This is a better random player, in that at least
    every move has an equal chance of being made.
    """
    # moves is a list of [(from, piece, moves), ...]
    # [((0, 1), 'P', [(0, 2), (0, 3)]), ...]
    tofrom = []
    for move in moves:
        fromPos = move[0]
        for toPos  in move[2]:
            tofrom.append((fromPos, toPos))
    selection = random.choice(tofrom)
    fromPos = selection[0]
    toPos = selection[1]
    return fromPos, toPos

def player1(board, state, moves):
    """
    This player uses a static analysis of the board
    to pick a winning move.
    """
    # moves is a list of [(from, piece, moves), ...]
    # [((0, 1), 'P', [(0, 2), (0, 3)]), ...]
    # Firs, get a list of all moves:
    tofrom = []
    for move in moves:
        fromPos = move[0]
        for toPos  in move[2]:
            tofrom.append([fromPos, toPos, 0]) # place for score
    # Now, we go through and try each one on the board
    # and see what the results are:
    for move in tofrom:
        fromPos, toPos, score = move
        newboard = deepcopy(board)
        newstate = deepcopy(state)
        newboard.makeMove(newstate, fromPos, toPos)
        # go through board and return a score
        move[2] = staticAnalysis(newboard, newstate)
    tofrom.sort(key=lambda move: move[2]) # sort on score
    # return the highest from, to:
    return tofrom[-1][0], tofrom[-1][1]

def staticAnalysis(board, state):
    """
    This is given a board and state of what would happen
    if you made a particular move.
    """
    #print("Static analysis")
    #print("State.player:", state.player)
    #print(board)
    return evaluateColor(board, state, state.player) - evaluateColor(board, state, board.getOtherPlayer(state))

def evaluateColor(board, state, player):
    state.player = player
    #print("evaluateColor", state.player)
    total = random.random() # small random value
    for x in range(8):
        for y in range(8):
            color = board.getColor(x, y)
            piece = board.board[y][x].upper()
            if color == state.player:
                score = 0
                if piece == 'K':
                    score += 1000
                elif piece == 'Q':
                    score += 216
                elif piece == 'N':
                    score += 108
                elif piece == 'R':
                    score += 56
                elif piece == 'B':
                    score += 28
                elif piece == 'P':
                    score += 14 * distanceToBackRow(player, y)
                if board.isThreatened(state, x, y):
                    #print("%s at (%s,%s) is threatend" % (piece, x, y))
                    score *= .25
                total += score
    #if state.player == 'w':
    #    print(board)
    #    print(total)
    #    Myro.ask("Next?")
    return total

def distanceToBackRow(player, y):
    if player == 'w':
        return abs(y - 7)/7
    else:
        return y/7

if __name__ == "__main__":
    # Play a game:
    # black, white:
    #gplay(randomPlayer2, player1)
    play(randomPlayer2, player1)

## or interactively test:
## White goes first:
# state = State('w')
# board = ChessBoard()
# print(board)
## Get possible moves:
# moves = board.getMoves(state)
## Pick one
## Then, apply the move to the board:
# board.makeMove(state, fromPos, toPos)
## Switch players:
# state.player = board.getOtherPlayer(state)
# board.checkStatus(state)
## Anything but zero ends the game:
# print(state.game_result)
