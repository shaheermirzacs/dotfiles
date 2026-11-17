return {
  "shaheermirzacs/rex.nvim",
  opts = {
    review_instruction = [[
Treat these annotations as a planning and discussion request.
Answer questions and explain your recommendations per item. For annotations
requesting changes, describe the proposed change without implementing it.
Keep a numbered list of proposed changes, updating it as we discuss.
Do not edit files or run commands that modify state until I explicitly
authorize implementation. Agreement with an explanation or proposal alone
does not authorize implementation.
Once authorized, apply only the agreed changes within the approved scope.
]]
  }
}
