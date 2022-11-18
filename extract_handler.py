def resolve_source(source):
  sizes = {1: "b", 2: "w", 4: "d"}
  mask_for_size = {1: "0xFF", 2: "0xFFFF", 4: "0xFFFFFFFF"}
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
  shifts = {
    "ah":">> 8",
    "bh":">> 8",
    "ch":">> 8",
    "dh":">> 8",
  }
  # load up flattened tree
  sources = [source]
  todo = []
  output = []
  while sources:
    source = sources.pop()
    if type(source) in [LowLevelILSub, LowLevelILZx, LowLevelILSx, LowLevelILAnd, LowLevelILXor, LowLevelILOr, LowLevelILNot, LowLevelILLsl, LowLevelILLsr, LowLevelILRol, LowLevelILRor, LowLevelILAdd]:
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
      output.append(hex(value.constant))
    elif type(value) == LowLevelILRegSsa:
      output.append("%s_%s" % (value.src.reg.name, value.src.version))
    elif type(value) == LowLevelILRegSsaPartial:
      result = "(%s & %s_%s)" % (hex(masks[value.src.name]), value.full_reg.reg.name, value.full_reg.version)
      if value.src.name in shifts:
        result = "(%s %s)" % (result, shifts[value.src.name])
      output.append(result)
    elif type(value) == LowLevelILAdd:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s + %s)" % (lhs, rhs))
    elif type(value) == LowLevelILSub:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s - %s)" % (lhs, rhs))
    elif type(value) == LowLevelILAnd:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s & %s)" % (lhs, rhs))
    elif type(value) == LowLevelILXor:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s ^ %s)" % (lhs, rhs))
    elif type(value) == LowLevelILOr:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s | %s)" % (lhs, rhs))
    elif type(value) == LowLevelILLsl:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s << %s)" % (lhs, rhs))
    elif type(value) == LowLevelILLsr:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s >> %s)" % (lhs, rhs))
    elif type(value) == LowLevelILRol:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s & ((%s << %s) | (%s >> (%d - %s))))" % (mask_for_size[value.size], lhs, rhs, lhs, value.size*8, rhs))
    elif type(value) == LowLevelILRor:
      rhs = output.pop()
      lhs = output.pop()
      output.append("(%s & ((%s >> %s) | (%s << (%d - %s))))" % (mask_for_size[value.size], lhs, rhs, lhs, value.size*8, rhs))
    elif type(value) == LowLevelILZx:
      operand = output.pop()
      output.append("zx(%s, %s)" % (operand, value.size))
    elif type(value) == LowLevelILSx:
      operand = output.pop()
      output.append("sx(%s, %s)" % (operand, value.size))
    elif type(value) == LowLevelILNot:
      operand = output.pop()
      output.append("not(%s, %s)" % (operand, value.size))
    elif type(value) == LowLevelILLoadSsa:
      operand = output.pop()
      output.append("read_mem(%s,%s)" % (operand, value.size))
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
  shifts = {
    "ah":"<< 8",
    "bh":"<< 8",
    "ch":"<< 8",
    "dh":"<< 8",
  }
  if type(assignment) == LowLevelILSetRegSsa:
    return "%s = %s" % (resolve_dest(assignment.dest), resolve_source(assignment.src))
  elif type(assignment) == LowLevelILSetRegSsaPartial:
    previous_version = "%s_%s" % (assignment.full_reg.reg, assignment.full_reg.version - 1)
    output = resolve_dest(assignment.full_reg)
    original = "(%s & %s)" % (hex(inverse_masks[assignment.dest.name]), previous_version)
    change = "(%s & %s)" % (hex(masks[assignment.dest.name]), resolve_source(assignment.src))
    full_src = "%s & %s" % (original, change)
    if assignment.dest.name in shifts:
      full_src = "(%s %s)" % (full_src, shifts[assignment.dest.name])
    return "%s = %s" % (output, full_src)
  else:
    raise Exception("Couldn't resolve assignment %s type %s" % (assignment, type(assignment)))

def find_dependent_registers(assignment):
  if type(assignment) not in [LowLevelILSetRegSsa, LowLevelILSetRegSsaPartial]:
    raise Exception("Couldn't resolve assignment %s type %s" % (assignment, type(assignment)))
  # load up flattened tree
  sources = [assignment.src]
  todo = []
  output = []
  while sources:
    source = sources.pop()
    if type(source) in [LowLevelILSub, LowLevelILZx, LowLevelILSx, LowLevelILAnd, LowLevelILXor, LowLevelILOr, LowLevelILNot, LowLevelILLsl, LowLevelILLsr, LowLevelILRol, LowLevelILRor, LowLevelILAdd]:
      for operand in source.operands:
        sources.append(operand)
    elif type(source) in [LowLevelILLoadSsa]:
      # operands are [src, src_memory] and src_memory is just an int ref we don't want
      sources.append(source.src)
    elif type(source) == LowLevelILRegSsa:
      output.append(source.src)
    elif type(source) == LowLevelILRegSsaPartial:
      output.append(source.full_reg)
    elif type(source) == LowLevelILConst:
      continue
    else:
      raise Exception("Couldn't process instruction %s type %s" % (source, type(source)))
  return output

def find_all_dependent_registers(func, llil_ssa, base_assignment):
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
  base_assignment = ls.get_ssa_reg_definition(register)
  if not base_assignment:
    log_info("Register not defined %s" % register_name)
    return []
  return find_all_dependent_registers(func, llil_ssa, base_assignment)
