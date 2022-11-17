from functools import reduce

func = bv.get_functions_containing(here)

ls = func.llil.ssa_form

# we get the latest version of our vars

ssa_reg = reduce(lambda x, y: x if x.version > y.version else y, filter(lambda x: x.reg == "esi", ls.ssa_registers))
ssa_ebx = reduce(lambda x, y: x if x.version > y.version else y, filter(lambda x: x.reg == "ebx", ls.ssa_registers))

reg_set = ls.get_ssa_reg_definition(ssa_reg)

src = reg_set.src

# ebx is hard with bl stuff
# check this out
# ebx#1.bl = ebx#0.bl ^ eax#7.al
# ebx#2 = ebx#1 ^ eax#16
# so we need to move all of ebx#0 across to ebx#1 apart from bl
# let's do the use case
# we want the output to be ebx#1 = (ebx#0 & 0xFFFFFF00) | (0x000000FF & ((0x000000FF & ebx#0) ^ (0x000000FF & eax#7)))
# that's a bit yuck
# problem we have is that it's not always a register as an operand
# e.g. <llil: eax#1 = zx.d([esi#1].b @ mem#0)>
# we have assign(eax#1, lowlevelzx(readmem(esi#1)))
# so this is annoying
# so we do need another function for resolving operands that dead-ends at registers/consts
# and another for printing the assignment
# maybe we just return a tree and do depth first for prints?

# this looks good, just need to handle the shifts from AH as ((eax >> 8) & 0xFF)
# and into AH as (val << 8) & 0xFF00

def resolve_source(source):
  sizes = {1: "b", 2: "w", 4: "d"}
  masks = {
    "al":0x000000FF,
    "bl":0x000000FF,
    "cl":0x000000FF,
    "dl":0x000000FF,
    "ah":0x0000FF00,
    "bh":0x0000FF00,
    "ch":0x0000FF00,
    "dh":0x0000FF00,
    "ax":0x0000FFFF,
    "bx":0x0000FFFF,
    "cx":0x0000FFFF,
    "dx":0x0000FFFF,
    "di":0x0000FFFF,
    "si":0x0000FFFF,
    "bp":0x0000FFFF,
    "sp":0x0000FFFF,
  }
  # load up flattened tree
  sources = [source]
  todo = []
  output = []
  while sources:
    source = sources.pop()
    if type(source) in [LowLevelILSub, LowLevelILZx, LowLevelILAnd, LowLevelILXor, LowLevelILOr, LowLevelILNot]:
      todo.append(source)
      for operand in source.operands:
        sources.append(operand)
    elif type(source) in [LowLevelILLoadSsa]:
      # operands are [src, src_memory] and src_memory is just an int ref we don't want
      todo.append(source)
      sources.append(source.src)
    elif type(source) in [LowLevelILConst, LowLevelILRegSsa, LowLevelILRegSsaPartial]:
      todo.append(source)
    else:
      raise Exception("Couldn't process instruction %s type %s" % (source, type(source)))
  # process flattened tree
  while todo:
    value = todo.pop()
    if type(value) == LowLevelILConst:
      output.append(value.constant)
    elif type(value) == LowLevelILRegSsa:
      output.append("%s_%s" % (value.src.reg.name, value.src.version))
    elif type(value) == LowLevelILRegSsaPartial:
      output.append("(%s & %s_%s)" % (hex(masks[value.src.name]), value.full_reg.reg.name, value.full_reg.version))
    elif type(value) == LowLevelILSub:
      lhs = output.pop()
      rhs = output.pop()
      output.append("(%s - %s)" % (lhs, rhs))
    elif type(value) == LowLevelILAnd:
      lhs = output.pop()
      rhs = output.pop()
      output.append("(%s & %s)" % (lhs, rhs))
    elif type(value) == LowLevelILXor:
      lhs = output.pop()
      rhs = output.pop()
      output.append("(%s ^ %s)" % (lhs, rhs))
    elif type(value) == LowLevelILOr:
      lhs = output.pop()
      rhs = output.pop()
      output.append("(%s | %s)" % (lhs, rhs))
    elif type(value) == LowLevelILZx:
      operand = output.pop()
      output.append("zx.%s(%s)" % (sizes[value.size], operand))
    elif type(value) == LowLevelILNot:
      operand = output.pop()
      output.append("~(%s)" % operand)
    elif type(value) == LowLevelILLoadSsa:
      operand = output.pop()
      output.append("[%s].%s" % (operand, sizes[value.size]))
    else:
      raise Exception("Couldn't process %s" % value)
  if len(output) != 1:
    raise Exception("expected one result but got %s" % output)
  return output[0]

def resolve_dest(dest):
  if type(dest) == SSARegister:
    return "%s_%s" % (dest.reg, dest.version)
  else:
    raise Exception("Couldn't resolve destination %s type %s" % (dest, type(dest)))

def resolve_assignment(assignment):
  masks = {
    "al":0x000000FF,
    "bl":0x000000FF,
    "cl":0x000000FF,
    "dl":0x000000FF,
    "ah":0x0000FF00,
    "bh":0x0000FF00,
    "ch":0x0000FF00,
    "dh":0x0000FF00,
    "ax":0x0000FFFF,
    "bx":0x0000FFFF,
    "cx":0x0000FFFF,
    "dx":0x0000FFFF,
    "di":0x0000FFFF,
    "si":0x0000FFFF,
    "bp":0x0000FFFF,
    "sp":0x0000FFFF,
  }
  inverse_masks = {
    "al":0xFFFFFF00,
    "bl":0xFFFFFF00,
    "cl":0xFFFFFF00,
    "dl":0xFFFFFF00,
    "ah":0xFFFF00FF,
    "bh":0xFFFF00FF,
    "ch":0xFFFF00FF,
    "dh":0xFFFF00FF,
    "ax":0xFFFF0000,
    "bx":0xFFFF0000,
    "cx":0xFFFF0000,
    "dx":0xFFFF0000,
    "di":0xFFFF0000,
    "si":0xFFFF0000,
    "bp":0xFFFF0000,
    "sp":0xFFFF0000,
  }
  if type(assignment) == LowLevelILSetRegSsa:
    return "%s = %s" % (resolve_dest(assignment.dest), resolve_source(assignment.src))
  elif type(assignment) == LowLevelILSetRegSsaPartial:
    previous_version = "%s_%s" % (assignment.full_reg.reg, assignment.full_reg.version - 1)
    return "%s = (%s & %s) | (%s & %s)" % (resolve_dest(assignment.full_reg), hex(inverse_masks[assignment.dest.name]), previous_version, hex(masks[assignment.dest.name]), resolve_source(assignment.src))
  else:
    raise Exception("Couldn't resolve assignment %s type %s" % (assignment, type(assignment)))
