import json
from lark import Transformer, v_args
from .wof_ast import *

@v_args(inline=True)
class ToAst(Transformer):
    # terminals -> Python values
    def NAME(self, t):    return str(t)
    def INT(self, t):     return int(t)
    def STRING(self, t):  return json.loads(str(t))   # handles \" and \n
    def POLICY(self, t):  return Policy(str(t))
    def VERDICT(self, t): return Verdict(str(t))

    # small pieces
    def type(self, name, star):  return TypeRef(name=name, many=star is not None)
    def condition(self, var, verdict):  return Condition(var=var, verdict=verdict)

    # members
    def redefinition(self, name, value): return Redefinition(name=name, value=value)
    def in_decl(self, name):             return In(name=name)
    def out_decl(self, name, t):         return Out(name=name, type_ref=t)
    def send_decl(self, name):           return Send(name=name)
    def body(self, *members):            return list(members)

    # statements
    def statement(self, step):           return step
    def input_decl(self, name, t):       return Input(name=name, type_ref=t)
    def init_decl(self, name, t, value): return Init(name=name, type_ref=t, value=value)
    def action_step(self, name, st, body):
        return Action(name=name, step_type=st, members=body)
    def spawn_step(self, count, name, st, policy, body):
        return Spawn(count=count, name=name, step_type=st, policy=policy, members=body)
    def reference_step(self, name, st, body):
        return Reference(name=name, step_type=st, members=body)
    def loop_step(self, name, retries, *rest):
        *stmts, cond = rest                    # the condition is always last
        return Loop(name=name, max_retries=retries, body=list(stmts), until=cond)

    def workflow(self, *stmts):
        return Workflow(statements=list(stmts))