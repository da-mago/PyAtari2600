#
# TIA
#
# Each TV line is updated at once when the line ends (probably at STA WSYNC instruction)
# Assume:
# - Background does not change during the line -> all line same color
# - Playfield can only change before each mid-line -> can be different for each midline -> store 1st midline as PFx_first
# - Each TRIGGER register (GP, missile, ball) is written 0 or 1 time a line -> Store at which pixel were triggered each one
#
# So, ... (draw all objects layer by layer. Order depends on some registers)
# - First, fill the whole line with the BG color
# - Second, draw the two Playfields
# - Third,  draw the ball
# - Fourth, draw GP0 and missile 0
# - Fourth, draw GP1 and missile 1
# - Reset tbe number of cycles at the end of each line. Assuming NTSC:
# First mid-line starts at cycle 68 and the second one at 148. HSYNC is at 228.
#
import numpy as np
import pygame

def print_debug(text):
    pass
    #print(text)

class TIA:

    dec2bin = [ [num & (0x80>>i) for i in range(8)] for num in range(256)]

    #
    # Registers
    #
    # Write-only
    VSYNC  = 0x00 #  0000 00x0   Vertical Sync Set-Clear
    VBLANK = 0x01 #  xx00 00x0   Vertical Blank Set-Clear
    WSYNC  = 0x02 #  ---- ----   Wait for Horizontal Blank
    RSYNC  = 0x03 #  ---- ----   Reset Horizontal Sync Counter
    NUSIZ0 = 0x04 #  00xx 0xxx   Number-Size player/missle 0
    NUSIZ1 = 0x05 #  00xx 0xxx   Number-Size player/missle 1
    COLUP0 = 0x06 #  xxxx xxx0   Color-Luminance Player 0
    COLUP1 = 0x07 #  xxxx xxx0   Color-Luminance Player 1
    COLUPF = 0x08 #  xxxx xxx0   Color-Luminance Playfield
    COLUBK = 0x09 #  xxxx xxx0   Color-Luminance Background
    CTRLPF = 0x0A #  00xx 0xxx   Control Playfield, Ball, Collisions
    REFP0  = 0x0B #  0000 x000   Reflection Player 0
    REFP1  = 0x0C #  0000 x000   Reflection Player 1
    PF0    = 0x0D #  xxxx 0000   Playfield Register Byte 0
    PF1    = 0x0E #  xxxx xxxx   Playfield Register Byte 1
    PF2    = 0x0F #  xxxx xxxx   Playfield Register Byte 2
    RESP0  = 0x10 #  ---- ----   Reset Player 0
    RESP1  = 0x11 #  ---- ----   Reset Player 1
    RESM0  = 0x12 #  ---- ----   Reset Missle 0
    RESM1  = 0x13 #  ---- ----   Reset Missle 1
    RESBL  = 0x14 #  ---- ----   Reset Ball
    AUDC0  = 0x15 #  0000 xxxx   Audio Control 0
    AUDC1  = 0x16 #  0000 xxxx   Audio Control 1
    AUDF0  = 0x17 #  000x xxxx   Audio Frequency 0
    AUDF1  = 0x18 #  000x xxxx   Audio Frequency 1
    AUDV0  = 0x19 #  0000 xxxx   Audio Volume 0
    AUDV1  = 0x1A #  0000 xxxx   Audio Volume 1
    GRP0   = 0x1B #  xxxx xxxx   Graphics Register Player 0
    GRP1   = 0x1C #  xxxx xxxx   Graphics Register Player 1
    ENAM0  = 0x1D #  0000 00x0   Graphics Enable Missle 0
    ENAM1  = 0x1E #  0000 00x0   Graphics Enable Missle 1
    ENABL  = 0x1F #  0000 00x0   Graphics Enable Ball
    HMP0   = 0x20 #  xxxx 0000   Horizontal Motion Player 0
    HMP1   = 0x21 #  xxxx 0000   Horizontal Motion Player 1
    HMM0   = 0x22 #  xxxx 0000   Horizontal Motion Missle 0
    HMM1   = 0x23 #  xxxx 0000   Horizontal Motion Missle 1
    HMBL   = 0x24 #  xxxx 0000   Horizontal Motion Ball
    VDELP0 = 0x25 #  0000 000x   Vertical Delay Player 0
    VDELP1 = 0x26 #  0000 000x   Vertical Delay Player 1
    VDELBL = 0x27 #  0000 000x   Vertical Delay Ball
    RESMP0 = 0x28 #  0000 00x0   Reset Missle 0 to Player 0
    RESMP1 = 0x29 #  0000 00x0   Reset Missle 1 to Player 1
    HMOVE  = 0x2A #  ---- ----   Apply Horizontal Motion
    HMCLR  = 0x2B #  ---- ----   Clear Horizontal Move Registers
    CXCLR  = 0x2C #  ---- ----   Clear Collision Latches
    #
    # Read-only
    CXM0P  = 0x00 #  xx00 0000   Read Collision  M0-P1   M0-P0
    CXM1P  = 0x01 #  xx00 0000                   M1-P0   M1-P1
    CXP0FB = 0x02 #  xx00 0000                   P0-PF   P0-BL
    CXP1FB = 0x03 #  xx00 0000                   P1-PF   P1-BL
    CXM0FB = 0x04 #  xx00 0000                   M0-PF   M0-BL
    CXM1FB = 0x05 #  xx00 0000                   M1-PF   M1-BL
    CXBLPF = 0x06 #  x000 0000                   BL-PF   -----
    CXPPMM = 0x07 #  xx00 0000                   P0-P1   M0-M1
    INPT0  = 0x08 #  x000 0000   Read Pot Port 0
    INPT1  = 0x09 #  x000 0000   Read Pot Port 1
    INPT2  = 0x0A #  x000 0000   Read Pot Port 2
    INPT3  = 0x0B #  x000 0000   Read Pot Port 3
    INPT4  = 0x0C #  x000 0000   Read Input (Trigger) 0
    INPT5  = 0x0D #  x000 0000   Read Input (Trigger) 1
    
    #
    # Color mapping
    #
    # NTSC
    NTSC_colorMap = [0x000000, 0x404040, 0x6C6C6C, 0x909090, 0xB0B0B0, 0xC8C8C8, 0xDCDCDC, 0xECECEC, 
                     0x444400, 0x646410, 0x848424, 0xA0A034, 0xB8B840, 0xD0D050, 0xE8E85C, 0xFCFC68,
                     0x702800, 0x844414, 0x985C28, 0xAC783C, 0xBC8C4C, 0xCCA05C, 0xDCB468, 0xECC878,
                     0x841800, 0x983418, 0xAC5030, 0xC06848, 0xD0805C, 0xE09470, 0xECA880, 0xFCBC94,
                     0x880000, 0x9C2020, 0xB03C3C, 0xC05858, 0xD07070, 0xE08888, 0xECA0A0, 0xFCB4B4,
                     0x78005C, 0x8C2074, 0xA03C88, 0xB0589C, 0xC070B0, 0xD084C0, 0xDC9CD0, 0xECB0E0,
                     0x480078, 0x602090, 0x783CA4, 0x8C58B8, 0xA070CC, 0xB484DC, 0xC49CEC, 0xD4B0FC,
                     0x140084, 0x302098, 0x4C3CAC, 0x6858C0, 0x7C70D0, 0x9488E0, 0xA8A0EC, 0xBCB4FC,
                     0x000088, 0x1C209C, 0x3840B0, 0x505CC0, 0x6874D0, 0x7C8CE0, 0x90A4EC, 0xA4B8FC,
                     0x00187C, 0x1C3890, 0x3854A8, 0x5070BC, 0x6888CC, 0x7C9CDC, 0x90B4EC, 0xA4C8FC,
                     0x002C5C, 0x1C4C78, 0x386890, 0x5084AC, 0x689CC0, 0x7CB4D4, 0x90CCE8, 0xA4E0FC,
                     0x003C2C, 0x1C5C48, 0x387C64, 0x509C80, 0x68B494, 0x7CD0AC, 0x90E4C0, 0xA4FCD4,
                     0x003C2C, 0x1C5C48, 0x387C64, 0x509C80, 0x68B494, 0x7CD0AC, 0x90E4C0, 0xA4FCD4,
                     0x003C00, 0x205C20, 0x407C40, 0x5C9C5C, 0x74B474, 0x8CD08C, 0xA4E4A4, 0xB8FCB8,
                     0x143800, 0x345C1C, 0x507C38, 0x6C9850, 0x84B468, 0x9CCC7C, 0xB4E490, 0xC8FCA4,
                     0x2C3000, 0x4C501C, 0x687034, 0x848C4C, 0x9CA864, 0xB4C078, 0xCCD488, 0xE0EC9C,
                     0x442800, 0x644818, 0x846830, 0xA08444, 0xB89C58, 0xD0B46C, 0xE8CC7C, 0xFCE08C ]
    
    colorMap = [[color>>16, (color>>8)&0xff, color&0xff] for color in NTSC_colorMap]
    

    def __init__(self, system):

        # Global information (clk_cycles, memory, ...)
        self.system = system
        
        # Graphics position
        self.P0_pos = 0
        self.P1_pos = 0
        self.M0_pos = 0
        self.M1_pos = 0
        self.BL_pos = 0

        self.screen = np.zeros((160, 192+20, 3), dtype=np.uint8)

        # register table
        self.reg_w_table = [
            self.w_VSYNC  , self.w_VBLANK , self.w_WSYNC  , self.w_RSYNC  ,
            self.w_NUSIZ0 , self.w_NUSIZ1 , self.w_COLUP0 , self.w_COLUP1 ,
            self.w_COLUPF , self.w_COLUBK , self.w_CTRLPF , self.w_REFP0  ,
            self.w_REFP1  , self.w_PF0    , self.w_PF1    , self.w_PF2    ,
            self.w_RESP0  , self.w_RESP1  , self.w_RESM0  , self.w_RESM1  ,
            self.w_RESBL  , self.w_AUDC0  , self.w_AUDC1  , self.w_AUDF0  ,
            self.w_AUDF1  , self.w_AUDV0  , self.w_AUDV1  , self.w_GRP0   ,
            self.w_GRP1   , self.w_ENAM0  , self.w_ENAM1  , self.w_ENABL  ,
            self.w_HMP0   , self.w_HMP1   , self.w_HMM0   , self.w_HMM1   ,
            self.w_HMBL   , self.w_VDELP0 , self.w_VDELP1 , self.w_VDELBL ,
            self.w_RESMP0 , self.w_RESMP1 , self.w_HMOVE  , self.w_HMCLR  ,
            self.w_CXCLR ]

#        self.reg_r_table = [
#            self.r_CXM0P  , self.r_CXM1P  , self.r_CXP0FB , self.r_CXP1FB ,
#            self.r_CXM0FB , self.r_CXM1FB , self.r_CXBLPF , self.r_CXPPMM ,
#            self.r_INPT0  , self.r_INPT1  , self.r_INPT2  , self.r_INPT3  ,
#            self.r_INPT4  , self.r_INPT5 ]

        # TIA signals
        self.vsync = 0
        self.wsync = 0
        self.rsync = 0
        self.line  = 0
        self.frame_cnt = 0

        self.colubk = [[0,0]] # List of background colour changes during the line

        # Playfield (40 bits)
        self.pf0_l = self.pf0_r = self.pf1_l = self.pf1_r = self.pf2_l = self.pf2_r = 0
        self.ppf_mirror = 0

        # Sprites
        self.P0_GR = np.zeros((3,3), dtype=np.uint8)
        self.P1_GR = np.zeros((3,3), dtype=np.uint8)
        self.M0_GR = np.zeros((3,3), dtype=np.uint8)
        self.M1_GR = np.zeros((3,3), dtype=np.uint8)
        self.BL_GR = np.zeros((3), dtype=np.uint8)
        self.GRP_size   = [1,  1,  1,  1,  1, 2,  1, 4]
        self.GRP_dist   = [0, 16, 32, 16, 64, 0, 32, 0]
        self.GRP_copies = [1,  2,  2,  3,  2, 1,  3, 1]

        self.P0_line = np.zeros((160,), dtype=np.bool)
        self.P1_line = np.zeros((160,), dtype=np.bool)
        self.M0_line = np.zeros((160,), dtype=np.bool)
        self.M1_line = np.zeros((160,), dtype=np.bool)
        self.BL_line = np.zeros((160,), dtype=np.bool)
        self.PF_line = np.zeros((160,), dtype=np.bool)
        self.PF0_line = np.zeros((80,), dtype=np.bool) # PF (left PF)
        self.PF1_line = np.zeros((80,), dtype=np.bool) # PF (right PF)
        
        self.pf0ToBin = np.array([[ j&(0x01<<i) for i in range(4)] for j in range(16)]).repeat(4, axis=1)
        self.pf1ToBin = np.array([[ j&(0x80>>i) for i in range(8)] for j in range(256)]).repeat(4, axis=1)
        self.pf2ToBin = np.array([[ j&(0x01<<i) for i in range(8)] for j in range(256)]).repeat(4, axis=1)
        self.pf0ToBinR = [ vec[::-1] for vec in self.pf0ToBin]
        self.pf1ToBinR = [ vec[::-1] for vec in self.pf1ToBin]
        self.pf2ToBinR = [ vec[::-1] for vec in self.pf2ToBin]


        pygame.init()
        # Scaling by is faster than using pygame.SCALED flag
        self.display = pygame.display.set_mode([320*3,(192+20)*3])
        self.surface = pygame.Surface((160, 192+20))

    def write(self, addr):
        ''' TIA register write operation '''
        if addr < len(self.reg_w_table):
            self.reg_w_table[addr]()
        else:
            print('Non=existing register')

    def read(self, addr):
        ''' TIA register read operation 
            Read address space relocated to 0x100-0x10D to avoid collision with
            write address space
        '''
        if addr <= INPT5:
            return self.system.memory[addr | 0x100]
#        if addr < len(self.reg_r_table):
#            reg_r_table[addr]()
        else:
            print('Non-existing register')
            return 0

    def dump(self):
        print("\nTIA registers\nWrite-only")
        print("-----------------------------------------------")
        for i in range(0,0x2C, 0x10):
            print(("{:02X} "*0x10).format(*memory[i:i+0x10]))
        print("\nRead-only")
        print("-----------------------------------------------")
        for i in range(0x100,0x10D, 0x10):
            print(("{:02X} "*0x10).format(*memory[i:i+0x10]))

    #
    # Register read/write
    #
    def w_VSYNC(self):
#        print_debug_debug("VSYNC val:{}, clk_cycles:{}, total_cycles:{}, line:{}".format(value, clk_cycles, total_cycles, line))
        #if value != 0:
        #    self.vsync = 1
        #else:
        #    if self.vsync == 1:
        #        self.vsync = 2

        # vsync negative edge
        if self.system.memory[TIA.VSYNC] == 0 and self.vsync != 0:
            self.vsync = 2

        self.vsync = self.system.memory[TIA.VSYNC] 

        #if self.system.memory[TIA.VSYNC] != 0:
        #    self.vsync

    def w_VBLANK(self):
        print_debug("VBLANK not yet implmented")

    def w_WSYNC(self):
        #clk_cycles = 228 # NTSC
        self.wsync = 1
        #print_debug_debug('WSYNC line {}, PC {}'.format(line, hex(PC)))
        self.system.clk_cycles = 228

    def w_RSYNC(self):
        self.rsync = 1
        self.system.clk_cycles = 225
        print_debug("RSYNC not yet implmented")

    def w_NUSIZ0(self):
        print_debug("NUSIZE0 not yet implmented")

    def w_NUSIZ1(self):
        print_debug("NUSIZE1 not yet implmented")

    def w_COLUP0(self):
        print_debug("COLUP0 not yet implmented")
        
    def w_COLUP1(self):
        print_debug("COLUP1 not yet implmented")

    def w_COLUPF(self):
        print_debug("COLUPF not yet implmented")

    def w_COLUBK(self):
        #cycles = clk_cycles - 68 if clk_cycles >= 68 else 0
        #colubk.append([cycles, value])
        if self.system.clk_cycles >= 68:
            self.colubk.append([self.system.clk_cycles - 68,
                                self.system.memory[TIA.COLUBK]])
        else:
            self.colubk[0] = [0, self.system.memory[TIA.COLUBK]]
        #print_debug('COLUBK', value, line)

    def w_CTRLPF(self):
        if self.system.clk_cycles < 148: # Before half-line
            self.pf_mirror = 1 if self.system.memory[TIA.CTRLPF] & 0x01 else 0

    def w_REFP0(self):
        print_debug("REFP0 not yet implmented")

    def w_REFP1(self):
        print_debug("REFP1 not yet implmented")

    def w_PF0(self):
        if self.system.clk_cycles < 48:
            self.pf0_l = self.system.memory[TIA.PF0]
            self.pf0_r = self.system.memory[TIA.PF0]
        elif self.system.clk_cycles < 148:
            self.pf0_r = self.system.memory[TIA.PF0]
            #TODO>review... upto 228

    def w_PF1(self):
        if self.system.clk_cycles < 84:
            self.pf1_l = self.system.memory[TIA.PF1]
            self.pf1_r = self.system.memory[TIA.PF1]
        elif self.system.clk_cycles < 164:
            self.pf1_r = self.system.memory[TIA.PF1]

    def w_PF2(self):
        if self.system.clk_cycles < 116:
            self.pf2_l = self.system.memory[TIA.PF2]
            self.pf2_r = self.system.memory[TIA.PF2]
        elif self.system.clk_cycles < 196:
            self.pf2_r = self.system.memory[TIA.PF2]

    def w_RESP0(self):
        # Single scalar, so assumng a single update during the line
        self.P0_pos = self.system.clk_cycles - 68 + 5 if self.system.clk_cycles >= 68 else 1
        #print_debug_debug("RESP0 pos:{}, line:{}, frame_cnt:{}".format(P0_pos, line, frame_cnt))

    def w_RESP1(self):
        self.P1_pos = self.system.clk_cycles - 68 + 5 if self.system.clk_cycles >= 68 else 1
        #print_debug_debug("RESP1 pos:{}".format(P0_pos))

    def w_RESM0(self):
        self.M0_pos = self.system.clk_cycles - 68 if self.system.clk_cycles >= 68 else 1

    def w_RESM1(self):
        self.M1_pos = self.system.clk_cycles - 68 if self.system.clk_cycles >= 68 else 1

    def w_RESBL(self):
        self.BL_pos = self.system.clk_cycles - 68 if self.system.clk_cycles >= 68 else 1

    def w_AUDC0(self):
        print_debug("AUDC0 not yet implmented")

    def w_AUDC1(self):
        print_debug("AUDC1 not yet implmented")

    def w_AUDF0(self):
        print_debug("AUDF0 not yet implmented")

    def w_AUDF1(self):
        print_debug("AUDF1 not yet implmented")

    def w_AUDV0(self):
        print_debug("AUDV0 not yet implmented")

    def w_AUDV1(self):
        print_debug("AUDV1 not yet implmented")

    def w_GRP0(self):
        # Add color
        #TODO: access to memory
        nusiz0 = self.system.memory[TIA.NUSIZ0] & 0x07
        size   = self.GRP_size[nusiz0]
        dist   = self.GRP_dist[nusiz0]
        copies = self.GRP_copies[nusiz0]
        
        grp = self.system.memory[TIA.GRP0]

        if copies == 1:
            if self.system.clk_cycles < (self.P0_pos + 68):
                self.P0_GR[0,:] = [grp, self.P0_pos, size]
        elif copies == 2:
            if self.system.clk_cycles < (self.P0_pos + 68):
                self.P0_GR[0,:] = [grp, self.P0_pos, size]
            elif self.system.clk_cycles < (self.P0_pos + 68 + dist):
                #TODO; esta variable (pos) no existe... yas'i estaba originalmente
                self.P0_GR[1,:] = [grp, pos, size]
        elif copies == 3:
            if self.system.clk_cycles < (self.P0_pos + 68):
                self.P0_GR[0,:] = [grp, self.P0_pos, size]
            elif self.system.clk_cycles < (self.P0_pos + 68 + dist):
                self.P0_GR[1,:] = [grp, pos, size]
            elif self.system.clk_cycles < (self.P0_pos + 68 + 2*dist):
                self.P0_GR[2,:] = [grp, pos, size]


        #TODO codigo no adaptado
        #grp_wr = True
        #grp = memory[GRP0]
        #if grp != -1:
        #    nusiz0 = memory[NUSIZ0] & 0x07
        #    size   = GRP_size[nusiz0]
        #    dist   = GRP_dist[nusiz0]
        #    copies = GRP_copies[nusiz0]
        #    data = np.repeat(dec2bin[grp], size)
        #    if memory[REFP0] & 0x08:
        #        data = data[::-1]

        #    if self.system.clk_cycles < (P0_pos + 68):
        #        P0_line[:] = 0
        #        P0_line[P0_pos : P0_pos+(8*size)] = data

        #    if copies>1:
        #        pos = P0_pos + dist
        #        if self.system.clk_cycles < (pos + 68):
        #            P0_line[pos : pos+(8*size)] = data

        #    if copies>2:
        #        pos = P0_pos + 2*dist
        #        if self.system.clk_cycles < (pos + 68):
        #            P0_line[pos : pos+(8*size)] = data

    def w_GRP1(self):
        #print_debug('GRP1', value, line, frame_cnt, self.system.clk_cycles/3, memory[0xb3], memory[0xa6])
        nusiz1 = self.system.memory[TIA.NUSIZ1] & 0x07
        size   = self.GRP_size[nusiz1]
        dist   = self.GRP_dist[nusiz1]
        copies = self.GRP_copies[nusiz1]
        
        grp = self.system.memory[TIA.GRP1]

        if copies == 1:
            if self.system.clk_cycles < (self.P1_pos + 68):
                self.P1_GR[0,:] = [grp, self.P1_pos, size]
        elif copies == 2:
            if self.system.clk_cycles < (self.P1_pos + 68):
                self.P1_GR[0,:] = [grp, self.P1_pos, size]
            elif self.system.clk_cycles < (self.P1_pos + 68 + dist):
                self.P1_GR[1,:] = [grp, pos, size]
        elif copies == 3:
            if self.system.clk_cycles < (self.P1_pos + 68):
                self.P1_GR[0,:] = [grp, self.P1_pos, size]
            elif self.system.clk_cycles < (self.P1_pos + 68 + dist):
                self.P1_GR[1,:] = [grp, pos, size]
            elif self.system.clk_cycles < (self.P1_pos + 68 + 2*dist):
                self.P1_GR[2,:] = [grp, pos, size]

    def w_ENAM0(self):
        print_debug("ENAM0 not yet implmented")

    def w_ENAM1(self):
        print_debug("ENAM1 not yet implmented")

    def w_ENABL(self):
        print_debug("ENABL not yet implmented")

    def w_HMP0(self):
        print_debug("HMP0 not yet implmented")

    def w_HMP1(self):
        print_debug("HMP1 not yet implmented")

    def w_HMM0(self):
        print_debug("HMM0 not yet implmented")

    def w_HMM1(self):
        print_debug("HMM1 not yet implmented")

    def w_HMBL(self):
        print_debug("HMBL not yet implmented")

    def w_VDELP0(self):
        print_debug("VDELP0 not yet implmented")

    def w_VDELP1(self):
        print_debug("VDELP1 not yet implmented")

    def w_VDELBL(self):
        print_debug("VDELBL not yet implmented")

    def w_RESMP0(self):
        if (self.system.memory[TIA.RESMP0] >> 1) & 0x01:
            self.M0_pos = self.P0_pos + 4 # Middle of the P0

    def w_RESMP1(self):
        if (self.system.memory[TIA.RESMP1]  >> 1) & 0x01:
            self.M1_pos = self.P1_pos + 4 # Middle of the P1

    def w_HMOVE(self):
        memory = self.system.memory
        tmp = memory[TIA.HMP0] >> 4
        self.P0_pos -= tmp if tmp < 8 else (tmp - 16)   # -8 ... +7
        tmp = self.system.memory[TIA.HMP1] >> 4
        self.P1_pos -= tmp if tmp < 8 else (tmp - 16)
        tmp = memory[TIA.HMM0] >> 4
        self.M0_pos -= tmp if tmp < 8 else (tmp - 16)
        tmp = memory[TIA.HMM1] >> 4
        self.M1_pos -= tmp if tmp < 8 else (tmp - 16)
        tmp = memory[TIA.HMBL] >> 4
        self.BL_pos -= tmp if tmp < 8 else (tmp - 16)

    def w_HMCLR(self):
        memory = self.system.memory
        memory[TIA.HMP0] = 0
        memory[TIA.HMP1] = 0
        memory[TIA.HMM0] = 0
        memory[TIA.HMM1] = 0
        memory[TIA.HMBL] = 0

    def w_CXCLR(self):
        for i in range(8):
            self.system.memory[0x100 + i] = 0

    #
    # Draw
    #
    def draw_line(self):
        '''
        Instead of updating display in real time, we'll keep track of any operation
        done over TIA registers and then we'll update the whole line at once
        '''
        memory = self.system.memory
        
        line_visible = self.line - 40
        screen_line = self.screen[:, line_visible]
        
        # Update background
        s2 = self.colubk[0][0]
        for i in range(len(self.colubk) - 1):
            s1 = s2
            s2 = self.colubk[i+1][0]
            color = TIA.colorMap[self.colubk[i][1]>>1]
            screen_line[s1:s2] = color
        color = TIA.colorMap[(self.colubk[-1][1]>>1)]
        screen_line[s2:160] = color
        
        # Priority depends on CTRLPF.D2: assume it is 0 at this moment
        # PF color depends on CTRLPF D1: assume it is 0 at this moment (so use COLUPF)
        # PF reflection depends on CTRLPF D0: assume it is 0 at this moment (so no mirror)
        
        # Update PlayFields
        # Simplification: assume color changes, at most, once each line 
        if memory[TIA.CTRLPF] & 0x02:
            PF_color1 = TIA.colorMap[memory[TIA.COLUP0]>>1]
            PF_color2 = TIA.colorMap[memory[TIA.COLUP1]>>1]
        else:
            PF_color1 = TIA.colorMap[memory[TIA.COLUPF]>>1]
            PF_color2 = PF_color1
    
        #a1 = time.clock()
        #a1 = time.time()
    
        # left-side display
        #if pf0_l & 0x10: 
        #    screen_line[0:4]   = PF_color1
        #if pf0_l & 0x20: 
        #    screen_line[4:8]   = PF_color1
        #if pf0_l & 0x40: 
        #    screen_line[8:12]  = PF_color1
        #if pf0_l & 0x80: 
        #    screen_line[12:16] = PF_color1
        #if pf1_l & 0x80:
        #    screen_line[16:20] = PF_color1
        #if pf1_l & 0x40:
        #    screen_line[20:24] = PF_color1
        #if pf1_l & 0x20:
        #    screen_line[24:28] = PF_color1
        #if pf1_l & 0x10:
        #    screen_line[28:32] = PF_color1
        #if pf1_l & 0x08:
        #    screen_line[32:36] = PF_color1
        #if pf1_l & 0x04:
        #    screen_line[36:40] = PF_color1
        #if pf1_l & 0x02:
        #    screen_line[40:44] = PF_color1
        #if pf1_l & 0x01:
        #    screen_line[44:48] = PF_color1
        #if pf2_l & 0x01:
        #    screen_line[48:52] = PF_color1
        #if pf2_l & 0x02:
        #    screen_line[52:56] = PF_color1
        #if pf2_l & 0x04:
        #    screen_line[56:60] = PF_color1
        #if pf2_l & 0x08:
        #    screen_line[60:64] = PF_color1
        #if pf2_l & 0x10:
        #    screen_line[64:68] = PF_color1
        #if pf2_l & 0x20:
        #    screen_line[68:72] = PF_color1
        #if pf2_l & 0x40:
        #    screen_line[72:76] = PF_color1
        #if pf2_l & 0x80:
        #    screen_line[76:80]= PF_color1
    
        ## right-side
        #if not pf_mirror:
        #    if pf0_r & 0x10: 
        #        screen_line[80:84]   = PF_color2
        #    if pf0_r & 0x20: 
        #        screen_line[84:88]   = PF_color2
        #    if pf0_r & 0x40: 
        #        screen_line[88:92]   = PF_color2
        #    if pf0_r & 0x80: 
        #        screen_line[92:96]   = PF_color2
        #    if pf1_r & 0x80: 
        #        screen_line[96:100]  = PF_color2
        #    if pf1_r & 0x40: 
        #        screen_line[100:104] = PF_color2
        #    if pf1_r & 0x20: 
        #        screen_line[104:108] = PF_color2
        #    if pf1_r & 0x10: 
        #        screen_line[108:112] = PF_color2
        #    if pf1_r & 0x08: 
        #        screen_line[112:116] = PF_color2
        #    if pf1_r & 0x04: 
        #        screen_line[116:120] = PF_color2
        #    if pf1_r & 0x02: 
        #        screen_line[120:124] = PF_color2
        #    if pf1_r & 0x01: 
        #        screen_line[124:128] = PF_color2
        #    if pf2_r & 0x01: 
        #        screen_line[128:132] = PF_color2
        #    if pf2_r & 0x02: 
        #        screen_line[132:136] = PF_color2
        #    if pf2_r & 0x04: 
        #        screen_line[136:140] = PF_color2
        #    if pf2_r & 0x08: 
        #        screen_line[140:144] = PF_color2
        #    if pf2_r & 0x10: 
        #        screen_line[144:148] = PF_color2
        #    if pf2_r & 0x20: 
        #        screen_line[148:152] = PF_color2
        #    if pf2_r & 0x40: 
        #        screen_line[152:156] = PF_color2
        #    if pf2_r & 0x80: 
        #        screen_line[156:160] = PF_color2
        #else:
        #    if pf2_r & 0x80: 
        #        screen_line[80:84]   = PF_color2
        #    if pf2_r & 0x40: 
        #        screen_line[84:88]   = PF_color2
        #    if pf2_r & 0x20: 
        #        screen_line[88:92]   = PF_color2
        #    if pf2_r & 0x10: 
        #        screen_line[92:96]   = PF_color2
        #    if pf2_r & 0x08: 
        #        screen_line[96:100]  = PF_color2
        #    if pf2_r & 0x04: 
        #        screen_line[100:104] = PF_color2
        #    if pf2_r & 0x02: 
        #        screen_line[104:108] = PF_color2
        #    if pf2_r & 0x01: 
        #        screen_line[108:112] = PF_color2
        #    if pf1_r & 0x01: 
        #        screen_line[112:116] = PF_color2
        #    if pf1_r & 0x02: 
        #        screen_line[116:120] = PF_color2
        #    if pf1_r & 0x04: 
        #        screen_line[120:124] = PF_color2
        #    if pf1_r & 0x08: 
        #        screen_line[124:128] = PF_color2
        #    if pf1_r & 0x10: 
        #        screen_line[128:132] = PF_color2
        #    if pf1_r & 0x20: 
        #        screen_line[132:136] = PF_color2
        #    if pf1_r & 0x40: 
        #        screen_line[136:140] = PF_color2
        #    if pf1_r & 0x80: 
        #        screen_line[140:144] = PF_color2
        #    if pf0_r & 0x80: 
        #        screen_line[144:148] = PF_color2
        #    if pf0_r & 0x40: 
        #        screen_line[148:152] = PF_color2
        #    if pf0_r & 0x20: 
        #        screen_line[152:156] = PF_color2
        #    if pf0_r & 0x10: 
        #        screen_line[156:160] = PF_color2
    
    
        #k=0
        #for j in range(8):
        #    if pf0_l & (0x10<<j) and j < 4: 
        #        screen_line[k:k+4]     = PF_color1
        #    if pf1_l & (0x80>>j): 
        #        screen_line[k+16:k+20] = PF_color1
        #    if pf2_l & (0x01<<j): 
        #        screen_line[k+48:k+52] = PF_color1
        #    if not pf_mirror:
        #        if pf0_r & (0x10<<j) and j < 4: 
        #            screen_line[k+80:k+84]   = PF_color2 # Assuming no mirror
        #        if pf1_r & (0x80>>j): 
        #            screen_line[k+96:k+100]  = PF_color2
        #        if pf2_r & (0x01<<j): 
        #            screen_line[k+128:k+132] = PF_color2
        #    else:
        #        if pf2_r & (0x80>>j): 
        #            screen_line[k+80:k+84]   = PF_color2 # Assuming mirror
        #        if pf1_r & (0x01<<j): 
        #            screen_line[k+112:k+116] = PF_color2
        #        if pf0_r & (0x80>>j) and j < 4: 
        #            screen_line[k+144:k+148] = PF_color2 # Assuming no mirror
        #    k += 4
    
        #a2 = time.clock()
#        a2 = time.time()
        #print(a2-a1)
    
        # Update PplayField
        #TODO: actually 0 is a valid color... it should be used a different code to indicate pixel enabled
        screen_line[0:80][self.PF0_line>0] = PF_color1
        screen_line[80:][self.PF1_line>0] = PF_color2
    
        # Update GPs and missiles
        size = 1
        P0_color = TIA.colorMap[memory[TIA.COLUP0]>>1] # assuming no change in color during the first half-line
        P1_color = TIA.colorMap[memory[TIA.COLUP1]>>1] # idem for second half-line
    
        # Update Players 0 and 1
        screen_line[self.P0_line>0] = P0_color
        screen_line[self.P1_line>0] = P1_color
    
        # Update Missiles
        screen_line[self.M0_line>0] = P0_color
        screen_line[self.M1_line>0] = P1_color
    
        # Update Ball
        BL_color = TIA.colorMap[memory[TIA.COLUPF]>>1]
        screen_line[self.BL_line>0] = BL_color

    def line_update(self):

        if self.line >= 40 and self.line < (232 + 20):

            # Playfield
            self.PF_line[0:16]  = self.pf0ToBin[self.pf0_l >> 4]
            self.PF_line[16:48] = self.pf1ToBin[self.pf1_l]
            self.PF_line[48:80] = self.pf2ToBin[self.pf2_l]
            if not self.pf_mirror:
                self.PF_line[80:96]  = self.pf0ToBin[self.pf0_r >> 4]
                self.PF_line[96:128] = self.pf1ToBin[self.pf1_r]
                self.PF_line[128:]   = self.pf2ToBin[self.pf2_r]
            else:
                self.PF_line[80:112]  = self.pf2ToBinR[self.pf2_r]
                self.PF_line[112:144] = self.pf1ToBinR[self.pf1_r]
                self.PF_line[144:]    = self.pf0ToBinR[self.pf0_r >> 4]

            self.PF0_line = self.PF_line[0:80]
            self.PF1_line = self.PF_line[80:]

            # Player 0
            #TODO SHIT! this need to be self
            nusiz0 = self.system.memory[TIA.NUSIZ0] & 0x07
            #TODO: dist and size should be used from P0_GR
            dist = self.GRP_dist[nusiz0]
            size = self.GRP_size[nusiz0]
            #TODO SHIT! this need to be self
            grpx = self.system.memory[TIA.GRP0]
            for i,(grp, _, _) in enumerate(self.P0_GR):
                if size == 0: 
                    grp  = grpx
                    dist = self.GRP_dist[nusiz0]
                    size = self.GRP_size[nusiz0]
                else:
                    grpx = grp

                pos = self.P0_pos + i*dist
                if grp != 0:
                    data = np.repeat(self.dec2bin[grp], size)
                    # TODO: we can add reverse arg as a new P0_GR item
                    if self.system.memory[TIA.REFP0] & 0x08:
                        data = data[::-1]
                    self.P0_line[pos : pos+len(data)] = data
        
            # Player 1
            nusiz1 = self.system.memory[TIA.NUSIZ1] & 0x07
            dist = self.GRP_dist[nusiz1]
            size = self.GRP_size[nusiz1]
            grpx = self.system.memory[TIA.GRP1]
            for i,(grp, _, size) in enumerate(self.P1_GR):
                if size == 0:
                    grp  = grpx
                    size = self.GRP_size[nusiz1]
                    dist = self.GRP_dist[nusiz1]
                else:
                    grpx = grp

                pos = self.P1_pos + i*dist
                if grp != 0:
                    data = np.repeat(self.dec2bin[grp], size)
                    if self.system.memory[TIA.REFP1] & 0x08:
                        data = data[::-1]

                    pos_end = pos+len(data)
                    if pos_end <= 160:
                        self.P1_line[pos : pos_end] = data
                    else:
                        tmp = pos_end - 160
                        pos_ini = len(data) - tmp
                        self.P1_line[pos : ] = data[ : pos_ini]
                        self.P1_line[ : tmp] = data[pos_ini :]


            # Missile 0
            for grp, pos, size in self.M0_GR:
                if grp != 0:
                    self.M0_line[pos : pos+size] = True
        
            # Missile 1
            for grp, pos, size in self.M1_GR:
                if grp != 0:
                    self.M1_line[pos : pos+size] = True
        
            # Ball
            grp, pos, size = self.BL_GR
            if grp != 0:
                self.BL_line[pos : pos+size] = True

            # Collisions
            if (self.P0_line & self.P1_line).any():
                print("Collision P0-P1")
                self.system.memory[0x107] |= 0x80
            if (self.P0_line & self.M0_line).any():
                print("Collision P0-M0")
                self.system.memory[0x100] |= 0x40
            if (self.P0_line & self.M1_line).any():
                print("Collision P0-M1")
                self.system.memory[0x101] |= 0x80
            if (self.P0_line & self.BL_line).any():
                print("Collision P0-BL")
                self.system.memory[0x102] |= 0x40
            if (self.P0_line & self.PF_line).any():
                print("Collision P0-PF")
                self.system.memory[0x102] |= 0x80

            if (self.P1_line & self.M0_line).any():
                print("Collision P1-M0")
                self.system.memory[0x100] |= 0x80
            if (self.P1_line & self.M1_line).any():
                print("Collision P1-M1")
                self.system.memory[0x101] |= 0x40
            if (self.P1_line & self.BL_line).any():
                print("Collision P1-BL")
                self.system.memory[0x103] |= 0x40
            if (self.P1_line & self.PF_line).any():
                print("Collision P1-PF")
                self.system.memory[0x103] |= 0x80

            if (self.M0_line & self.M1_line).any():
                print("Collision M0-M1")
                self.system.memory[0x107] |= 0x40
            if (self.M0_line & self.BL_line).any():
                print("Collision M0-BL")
                self.system.memory[0x104] |= 0x40
            if (self.M0_line & self.PF_line).any():
                print("Collision M0-PF")
                self.system.memory[0x104] |= 0x80

            if (self.M1_line & self.BL_line).any():
                print("Collision M1-BL")
                self.system.memory[0x105] |= 0x40
            if (self.M1_line & self.PF_line).any():
                print("Collision M1-PF")
                self.system.memory[0x105] |= 0x80

            if (self.BL_line & self.PF_line).any():
                print("Collision BL-PF")
                self.system.memory[0x106] |= 0x80

#        total_cycles += 228
        self.system.clk_cycles %= 228
#        print_debug("Line {}  PC={} cyles={}".format(line+1, hex(PC), clk_cycles/3))


        # Draw line
        if self.line >= 40 and self.line < (232 + 20):
            self.draw_line()

    def _prepare_next_line(self):
        # Prepare internal vars for the next line
        self.colubk    = [[0, self.system.memory[TIA.COLUBK]]]
        self.pf0_l     = self.pf0_r = self.system.memory[TIA.PF0]
        self.pf1_l     = self.pf1_r = self.system.memory[TIA.PF1]
        self.pf2_l     = self.pf2_r = self.system.memory[TIA.PF2]
        self.pf_mirror = 1 if self.system.memory[TIA.CTRLPF] & 0x01 else 0

        #memory[NUSIZ0] = 0
        nusiz0 = self.system.memory[TIA.NUSIZ0] & 0x07
        size   = self.GRP_size[nusiz0]
        dist   = self.GRP_dist[nusiz0]
        copies = self.GRP_copies[nusiz0]
        nusiz1 = self.system.memory[TIA.NUSIZ1] & 0x07
        size1  = self.GRP_size[nusiz1]
        dist1  = self.GRP_dist[nusiz1]
        copies1= self.GRP_copies[nusiz1]
        sizeM0 = 2 ** ((self.system.memory[TIA.NUSIZ0] >> 4) & 0x03)
        sizeM1 = 2 ** ((self.system.memory[TIA.NUSIZ1] >> 4) & 0x03)
        sizeB  = 2 ** ((self.system.memory[TIA.CTRLPF] >> 4) & 0x03)
        self.P0_GR[:,2] = 0
        self.P1_GR[:,2] = 0
        self.M0_GR[:,2] = 0
        self.M1_GR[:,2] = 0
        self.BL_GR[0] = 0
        for i in range(copies):
            self.M0_GR[i,0] = ((self.system.memory[TIA.ENAM0] >> 1) & 0x01) & ((~self.system.memory[TIA.RESMP0] >> 1) & 0x01)
            self.M0_GR[i,1] = self.M0_pos + i*dist
            self.M0_GR[i,2] = sizeM0
        for i in range(copies1):
            self.M1_GR[i,0] = ((self.system.memory[TIA.ENAM1] >> 1) & 0x01) & ((~self.system.memory[TIA.RESMP1] >> 1) & 0x01)
            self.M1_GR[i,1] = self.M1_pos + i*dist1
            self.M1_GR[i,2] = sizeM1
        self.BL_GR[0] = ((self.system.memory[TIA.ENABL] >> 1) & 0x01)
        self.BL_GR[1] = self.BL_pos
        self.BL_GR[2] = sizeB

        #P0_line_old = P0_line.copy()
        self.P0_line[:] = 0
        self.P1_line[:] = 0
        self.M0_line[:] = 0
        self.M1_line[:] = 0
        self.BL_line[:] = 0

        #grp = memory[GRP0]

        #if grp != 0:
        #    data = np.repeat(dec2bin[grp], size)
        #    if memory[REFP0] & 0x08:
        #        data = data[::-1]

        #    P0_line[P0_pos : P0_pos+(8*size)] = data
        #    if copies>1:
        #        pos = P0_pos + dist
        #        P0_line[pos : pos+(8*size)] = data
        #    if copies>2:
        #        pos = P0_pos + 2*dist
        #        P0_line[pos : pos+(8*size)] = data
        #    #if memory[GRP0] != 0: print(P0_line, memory[GRP0], line-40)

        #if grp == 0:
        #    P0_line[:] = 0

        self.line += 1


    def frame_update(self):
        #print_debug("frame {} line:{}".format(frame_cnt, line))
        self.line = 3

#        t2 = time.time()
#        print_debug("\nFRAME {}: line {}".format(frame_cnt, line))
#        print("{} Hz, frame {}".format( 1/(t2-t1), frame_cnt))
        #code.interact(local=locals())
        self.frame_cnt += 1
#        t1 = t2
        #if line >= 262:
        #    line = 0
        pygame.surfarray.blit_array(self.surface, self.screen)
        self.display.blit(pygame.transform.scale(self.surface, (320*3,(192+20)*3)), (0, 0))
        pygame.display.flip()
#        if frame_cnt == 4000:
#            break
        #time.sleep(1)
#        print("{} Hz, frame {}".format( 1/(t2-t1), frame_cnt))

        # Input keyboard
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_0:
                    self.system.memory[0x282] &= ~0x01    # reset
                elif event.key == pygame.K_1:
                    self.system.memory[0x282] &= ~0x02    # select
                elif event.key == pygame.K_l:
                    self.system.memory[0x280] &= ~0x80    # P0 right
                elif event.key == pygame.K_j:
                    self.system.memory[0x280] &= ~0x40    # P0 left
                elif event.key == pygame.K_k:
                    self.system.memory[0x280] &= ~0x20    # P0 down
                elif event.key == pygame.K_i:
                    self.system.memory[0x280] &= ~0x10    # P0 up
                elif event.key == pygame.K_d:
                    self.system.memory[0x280] &= ~0x08    # P1 right
                elif event.key == pygame.K_a:
                    self.system.memory[0x280] &= ~0x04    # P1 left
                elif event.key == pygame.K_s:
                    self.system.memory[0x280] &= ~0x02    # P1 down
                elif event.key == pygame.K_w:
                    self.system.memory[0x280] &= ~0x01    # P1 up
                elif event.key == pygame.K_2:
                    self.system.memory[0x282] ^= 0x80     # P0 difficulty 
                elif event.key == pygame.K_3:
                    self.system.memory[0x282] ^= 0x40     # P1 difficulty

                elif event.key == pygame.K_m:
                    self.system.memory[0x10C] &= ~0x80     # P0 button
                elif event.key == pygame.K_x:
                    self.system.memory[0x10D] &= ~0x80     # P1 button

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_0:
                    self.system.memory[0x282] |= 0x01
                elif event.key == pygame.K_1:
                    self.system.memory[0x282] |= 0x02
                elif event.key == pygame.K_l:
                    self.system.memory[0x280] |= 0x80    # P0 right
                elif event.key == pygame.K_j:
                    self.system.memory[0x280] |= 0x40    # P0 left
                elif event.key == pygame.K_k:
                    self.system.memory[0x280] |= 0x20    # P0 down
                elif event.key == pygame.K_i:
                    self.system.memory[0x280] |= 0x10    # P0 up
                elif event.key == pygame.K_d:
                    self.system.memory[0x280] |= 0x08    # P1 right
                elif event.key == pygame.K_a:
                    self.system.memory[0x280] |= 0x04    # P1 left
                elif event.key == pygame.K_s:
                    self.system.memory[0x280] |= 0x02    # P1 down
                elif event.key == pygame.K_w:
                    self.system.memory[0x280] |= 0x01    # P1 up

                elif event.key == pygame.K_m:
                    self.system.memory[0x10C] |= 0x80     # P0 button
                elif event.key == pygame.K_x:
                    self.system.memory[0x10D] |= 0x80     # P1 button
