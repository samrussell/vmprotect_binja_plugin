class AstNode(object):
  def __init__(self, value):
    self.value = value
  def __repr__(self):
    return "%s" % self.value

class AstNodeAssignment(AstNode):
  def __init__(self, dest, src):
    self.dest = dest
    self.src = src
  def __repr__(self):
    return "%s = %s" % (self.dest, self.src)

class AstNodeAssignmentPartial(AstNode):
  def __init__(self, dest, src):
    self.dest = dest
    self.src = src
  def __repr__(self):
    return "%s = %s" % (self.dest, self.src)

class AstNodeMemoryStore(AstNode):
  def __init__(self, dest, src):
    self.dest = dest
    self.src = src
  def __repr__(self):
    return "[%s] = %s" % (self.dest, self.src)

class AstNodeConstant(AstNode):
  def __repr__(self):
    return "0x%s" % hex(self.value)

class AstNodeRegisterSsa(AstNode):
  def __init__(self, name, version):
    self.name = name
    self.version = version
  def __repr__(self):
    return "%s#%s" % (self.name, self.version)
  def __hash__(self):
    return hash((self.name, self.version))
  def __eq__(self, other):
    return type(other) == type(self) \
      and self.name == other.name \
      and self.version == other.version

class AstNodeReadMem(AstNode):
  def __init__(self, operand, size):
    self.operand = operand
    self.size = size
  def __repr__(self):
    return "ReadMem(%s, %s)" % (self.operand, self.size)

class AstNodeZx(AstNode):
  def __init__(self, operand, size):
    self.operand = operand
    self.size = size
  def __repr__(self):
    return "Zx(%s, %s)" % (self.operand, self.size)

class AstNodeNot(AstNode):
  def __init__(self, operand, size):
    self.operand = operand
    self.size = size
  def __repr__(self):
    return "Not(%s, %s)" % (self.operand, self.size)

class AstNodeNeg(AstNode):
  def __init__(self, operand, size):
    self.operand = operand
    self.size = size
  def __repr__(self):
    return "Neg(%s, %s)" % (self.operand, self.size)

class AstNodeFlagBit(AstNode):
  def __init__(self, operand, bit):
    self.operand = operand
    self.bit = bit
  def __repr__(self):
    return "FlagBit(%s, %s)" % (self.operand, self.bit)

class AstNodeBswap(AstNode):
  def __init__(self, operand):
    self.operand = operand
  def __repr__(self):
    return "Bswap(%s)" % (self.operand)

class AstNodeBinaryOperation(AstNode):
  OPERATION = "NONE"
  def __init__(self, lhs, rhs):
    self.lhs = lhs
    self.rhs = rhs
  def __repr__(self):
    return "%s(%s, %s)" % (self.OPERATION, self.lhs, self.rhs)

class AstNodeSub(AstNodeBinaryOperation):
  OPERATION = "Sub"

class AstNodeAdd(AstNodeBinaryOperation):
  OPERATION = "Add"

class AstNodeRor(AstNodeBinaryOperation):
  OPERATION = "Ror"

class AstNodeRol(AstNodeBinaryOperation):
  OPERATION = "Rol"

class AstNodeShr(AstNodeBinaryOperation):
  OPERATION = "Shr"

class AstNodeShl(AstNodeBinaryOperation):
  OPERATION = "Shl"

class AstNodeXor(AstNodeBinaryOperation):
  OPERATION = "Xor"

class AstNodeOr(AstNodeBinaryOperation):
  OPERATION = "Or"

def try_lookup_register(name, version):
  if version == 0:
    return AstNodeRegisterSsa(name, version)

def resolve_source(source):
  # load up flattened tree
  sources = [source]
  todo = []
  output = []
  while sources:
    source = sources.pop()
    if type(source) in [LowLevelILSub, LowLevelILZx, LowLevelILSx, LowLevelILAnd, LowLevelILXor, LowLevelILOr, LowLevelILNot, LowLevelILLsl, LowLevelILLsr, LowLevelILRol, LowLevelILRor, LowLevelILAdd, LowLevelILNeg]:
      todo.append(source)
      for operand in source.operands:
        sources.append(operand)
    elif type(source) in [LowLevelILLoadSsa]:
      # operands are [src, src_memory] and src_memory is just an int ref we don't want
      todo.append(source)
      sources.append(source.src)
    elif type(source) in [LowLevelILConst, LowLevelILRegSsa, LowLevelILRegSsaPartial]:
      todo.append(source)
    elif type(source) == LowLevelILFlagBitSsa:
      # workaround, just pushes the class and no operands
      todo.append(source)
    else:
      raise Exception("Couldn't process instruction %s type %s" % (source, type(source)))
  # process flattened tree
  while todo:
    value = todo.pop()
    if type(value) == LowLevelILConst:
      output.append(AstNodeConstant(value.constant))
    elif type(value) == LowLevelILRegSsa:
      register = AstNodeRegisterSsa(value.src.reg.name, value.src.version)
      output.append(register)
    elif type(value) == LowLevelILSub:
      rhs = output.pop()
      lhs = output.pop()
      output.append(AstNodeSub(lhs, rhs))
    elif type(value) == LowLevelILLoadSsa:
      operand = output.pop()
      output.append(AstNodeReadMem(operand, value.size))
    elif type(value) == LowLevelILZx:
      operand = output.pop()
      output.append(AstNodeZx(operand, value.size))
    elif type(value) == LowLevelILNot:
      operand = output.pop()
      output.append(AstNodeNot(operand, value.size))
    elif type(value) == LowLevelILNeg:
      operand = output.pop()
      output.append(AstNodeNeg(operand, value.size))
    elif type(value) == LowLevelILFlagBitSsa:
      # ignore for now
      #bit = output.pop()
      #operand = output.pop()
      output.append(AstNodeFlagBit("dummy flag", 0xab))
    elif type(value) == LowLevelILAdd:
      rhs = output.pop()
      lhs = output.pop()
      output.append(AstNodeAdd(lhs, rhs))
    elif type(value) == LowLevelILXor:
      rhs = output.pop()
      lhs = output.pop()
      output.append(AstNodeXor(lhs, rhs))
    elif type(value) == LowLevelILOr:
      rhs = output.pop()
      lhs = output.pop()
      output.append(AstNodeOr(lhs, rhs))
    elif type(value) == LowLevelILRor:
      rhs = output.pop()
      lhs = output.pop()
      output.append(AstNodeRor(lhs, rhs))
    elif type(value) == LowLevelILRol:
      rhs = output.pop()
      lhs = output.pop()
      output.append(AstNodeRol(lhs, rhs))
    else:
      raise Exception("Couldn't process %s type %s" % (value, type(value)))
  if len(output) != 1:
    raise Exception("expected one result but got %s" % output)
  return output[0]

def resolve_dest(dest):
  if type(dest) == SSARegister:
    return AstNodeRegisterSsa(dest.reg.name, dest.version)
  else:
    raise Exception("Couldn't resolve destination %s type %s" % (dest, type(dest)))

def resolve_assignment(assignment):
  if type(assignment) == LowLevelILSetRegSsa:
    dest = resolve_dest(assignment.dest)
    source = resolve_source(assignment.src)
    return AstNodeAssignment(dest, source)
  elif type(assignment) == LowLevelILIntrinsicSsa:
    # this is specific opcodes
    intrinsic = assignment.intrinsic
    if type(intrinsic) == ILIntrinsic:
      source = resolve_dest(assignment.param.src[0].src)
      dest = AstNodeRegisterSsa(assignment.output[0].reg_or_flag.name, assignment.output[0].version)
      return AstNodeAssignment(dest, AstNodeBswap(source))
    else:
      raise Exception("Couldn't resolve intrinsict %s type %s" % (assignment, type(assignment.intrinsic)))
  elif type(assignment) == LowLevelILStoreSsa:
    # we use resolve_source because this will resolve to an expression
    dest = resolve_source(assignment.dest)
    source = resolve_source(assignment.src)
    return AstNodeMemoryStore(dest, source)
  else:
    raise Exception("Couldn't resolve assignment %s type %s" % (assignment, type(assignment)))

def build_ast(assignment):
  pass

def find_important_registers():
  # esi = vip
  # ebp = vsp
  # esp = pRegs
  # edi = pFunc
  # ebx = key
  pass

def find_dependent_registers(assignment):
  if type(assignment) in [LowLevelILSetRegSsa, LowLevelILSetRegSsaPartial]:
    sources = [assignment.src]
  elif type(assignment) == LowLevelILStoreSsa:
    sources = [assignment.src, assignment.dest]
  else:
    raise Exception("Couldn't resolve assignment %s type %s" % (assignment, type(assignment)))
  # load up flattened tree
  todo = []
  output = []
  while sources:
    source = sources.pop()
    if type(source) in [LowLevelILSub, LowLevelILZx, LowLevelILSx, LowLevelILAnd, LowLevelILXor, LowLevelILOr, LowLevelILNot, LowLevelILLsl, LowLevelILLsr, LowLevelILRol, LowLevelILRor, LowLevelILAdd, LowLevelILNeg]:
      for operand in source.operands:
        sources.append(operand)
    elif type(source) in [LowLevelILLoadSsa]:
      # operands are [src, src_memory] and src_memory is just an int ref we don't want
      sources.append(source.src)
    elif type(source) == LowLevelILRegSsa:
      output.append(source.src)
    elif type(source) == LowLevelILFlagBitSsa:
      # don't care for now
      continue
    elif type(source) == SSAFlag:
      # we should track these but also don't really care for now
      continue
      #output.append(source.src)
    elif type(source) == LowLevelILRegSsaPartial:
      output.append(source.full_reg)
    elif type(source) == LowLevelILConst or type(source) == int:
      continue
    else:
      raise Exception("Couldn't process instruction %s type %s" % (source, type(source)))
  return output

def find_all_dependent_registers(llil_ssa, base_assignment):
  assignments = [base_assignment]
  output_assignments = []
  while assignments:
    assignment = assignments.pop()
    log_info("Analysing assignment %s" % assignment)
    output_assignments.append(assignment)
    dependent_registers = find_dependent_registers(assignment)
    for register in dependent_registers:
      log_info("Adding dependent register %s" % register)
      assignment = llil_ssa.get_ssa_reg_definition(register)
      if assignment:
        log_info("Defined at: %s" % assignment)
        assignments.append(assignment)
      else:
        log_info("Register %s has no definition, skipping" % register)
  # convert to pythonesque
  output_python = []
  while output_assignments:
    output_python.append(resolve_assignment(output_assignments.pop()))
  return output_python

def find_all_dependent_registers_from_address(address):
  func = bv.get_functions_containing(address)[0]
  base_assignment = func.get_llil_at(address).ssa_form
  llil_ssa = func.llil.ssa_form
  return find_all_dependent_registers(func, llil_ssa, base_assignment)

def find_all_dependent_registers_from_register_name(func, register_name):
  llil_ssa = func.llil.ssa_form
  registers = sorted(filter(lambda x: x.reg.name==register_name, llil_ssa.ssa_registers), key=lambda x: x.version)
  if not registers:
    log_info("Register not mentioned %s" % register_name)
    return []
  register = registers[-1]
  base_assignment = llil_ssa.get_ssa_reg_definition(register)
  if not base_assignment:
    log_info("Register not defined %s" % register_name)
    return []
  return find_all_dependent_registers(llil_ssa, base_assignment)

def find_all_memory_writes(func):
  llil_ssa = func.llil.ssa_form
  store_instructions = list(filter(lambda x: isinstance(x, LowLevelILStoreSsa), llil_ssa.instructions))
  if not store_instructions:
    log_info("No store instructions found")
    return []
  
  assignments = []
  for store_instruction in store_instructions:
    assignments += find_all_dependent_registers(llil_ssa, store_instruction)
  
  return assignments

def evaluate_rol(value, amount):
  # we are assuming 32 bits which is going to be wrong later
  bits = 32
  mask = 0xFFFFFFFF
  return mask & ((value << amount) | (value >> (bits - amount)))

def evaluate_ror(value, amount):
  # we are assuming 32 bits which is going to be wrong later
  bits = 32
  mask = 0xFFFFFFFF
  return mask & ((value >> amount) | (value << (bits - amount)))

def evaluate_add(lhs, rhs):
  # we are assuming 32 bits which is going to be wrong later
  mask = 0xFFFFFFFF
  output = mask & (lhs + rhs)
  return output

def evaluate_sub(lhs, rhs):
  # we are assuming 32 bits which is going to be wrong later
  mask = 0xFFFFFFFF
  output = lhs - rhs
  while output < 0:
    output += (mask+1)
  return mask & output

def evaluate_value(value, assignments_by_register):
  masks_by_bits = {
    8: 0xFF,
    16: 0xFFFF,
    32: 0xFFFFFFFF
  }
  if isinstance(value, AstNodeRegisterSsa):
    assignment = assignments_by_register[value]
    return evaluate_value(assignment.src, assignments_by_register)
  elif isinstance(value, AstNodeConstant):
    return value.value
  elif isinstance(value, AstNodeAdd):
    lhs = evaluate_value(value.lhs, assignments_by_register)
    rhs = evaluate_value(value.rhs, assignments_by_register)
    return evaluate_add(lhs, rhs)
  elif isinstance(value, AstNodeSub):
    lhs = evaluate_value(value.lhs, assignments_by_register)
    rhs = evaluate_value(value.rhs, assignments_by_register)
    return evaluate_sub(lhs, rhs)
  elif isinstance(value, AstNodeRol):
    lhs = evaluate_value(value.lhs, assignments_by_register)
    rhs = evaluate_value(value.rhs, assignments_by_register)
    return evaluate_rol(lhs, rhs)
  elif isinstance(value, AstNodeRor):
    lhs = evaluate_value(value.lhs, assignments_by_register)
    rhs = evaluate_value(value.rhs, assignments_by_register)
    return evaluate_ror(lhs, rhs)
  elif isinstance(value, AstNodeNot):
    mask = masks_by_bits[value.size * 8]
    operand = evaluate_value(value.operand, assignments_by_register)
    return operand ^ mask
  elif isinstance(value, AstNodeNeg):
    operand = evaluate_value(value.operand, assignments_by_register)
    return 1 + masks_by_bits[value.size*8] - operand 
  elif isinstance(value, AstNodeXor):
    lhs = evaluate_value(value.lhs, assignments_by_register)
    rhs = evaluate_value(value.rhs, assignments_by_register)
    return lhs ^ rhs
  elif isinstance(value, AstNodeReadMem):
    # special case for esp
    if isinstance(value.operand, AstNodeAdd) and isinstance(value.operand.lhs, AstNodeRegisterSsa):
      add = value.operand
      if add.lhs.name == "esp" and evaluate_value(add.rhs, {}) == 0x28:
        return assignments_by_register["key"]
      else:
        raise Exception("Looks like ESP read but we didn't handle it? %s %s" % (value, type(add.rhs)))
    address = evaluate_value(value.operand, assignments_by_register)
    data = bv.read_int(address, value.size)
    while data < 0:
      data += (masks_by_bits[value.size * 8] + 1)
    return data
  else:
    raise Exception("Couldn't evalute %s type %s" % (value, type(value)))

def get_final_value(func, register_name, initial_registers):
  edi_vars = find_all_dependent_registers_from_register_name(func, register_name)
  edi_vars_by_name = {x.dest: x for x in edi_vars} | initial_registers
  return evaluate_value(edi_vars[-1].dest, edi_vars_by_name)

def evaluate_vmenter(func, key):
  initial_registers = {
    # this feels weird but recursion makes us do dumb things
    "key" : key,
    AstNodeRegisterSsa("esp", 0) : AstNodeAssignment(AstNodeRegisterSsa("esp", 0), AstNodeConstant(0xFFFF0000))
  }
  return {
    "edi": get_final_value(func, "edi", initial_registers),
    "esp": get_final_value(func, "esp", initial_registers),
    "ebp": get_final_value(func, "ebp", initial_registers),
    "ebx": get_final_value(func, "ebx", initial_registers),
    "esi": get_final_value(func, "esi", initial_registers)
  }
