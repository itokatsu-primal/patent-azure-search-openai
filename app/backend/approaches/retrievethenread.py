import openai
from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from text import nonewlines

# Cognitive SearchとOpenAIのAPIを直接使用した、retrieve-then-readの実装です。これは、最初に
# 検索からトップ文書を抽出し、それを使ってプロンプトを構成し、OpenAIで補完生成する 
# (answer)をそのプロンプトで表示します。

# Simple retrieve-then-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.
class RetrieveThenReadApproach(Approach):

    template = \
"あなたはリチウム硫黄電池の特許情報に関する質問をサポートする教師アシスタントです。" + \
"質問者が「私」で質問しても、「あなた」を使って質問者を指すようにする。" + \
"次の質問に、以下の出典で提供されたデータのみを使用して答えてください。" + \
"各出典元には、名前の後にコロンと実際の情報があり、回答で使用する各事実には必ず出典名を記載します。" + \
"以下の出典の中から答えられない場合は、「わかりません」と答えてください。" + \
"""

###
Question: 'リチウム硫黄電池の具体的な技術課題を教えてください'

Sources:
JP4227882B.pdf: 硫黄を活性物質として使用すると、投入された硫黄の量に対して電気化学的酸化還元反応に関与する硫黄の利用率が小さいため、ごく少量の電池容量しか得られない。
JP5445809B.pdf: 正極活物質として正極合材層に含まれる硫黄が電気絶縁性であるため、正極合材層における電子伝導性及びリチウムイオン伝導性が非常に低い。
JP7082405B.pdf:硫酸ナトリウムを炭素によって硫化リチウムに還元するには、高温の加熱工程が必要
JP2015506539.pdf: 硫黄カソードの放電では、充電－放電プロセス中に電解質に容易に溶解しかつサイクル動作中の活物質の不可逆的な損失をもたらす、中間体多硫化物イオンが形成される

Answer:
リチウム硫黄電池の具体的な技術課題には、硫黄量に対して電気化学的酸化還元反応に関与する硫黄の利用率が小さく電池容量が少量になること、[JP4227882B.pdf] 正極活物質として正極合材層に含まれる硫黄が電気絶縁性であるため正極合材層における電子伝導性及びリチウムイオン伝導性が非常に低いこと、[JP5445809B.pdf] 硫黄カソードの放電では、充電－放電プロセス中に電解質に容易に溶解しかつサイクル動作中の活物質の不可逆的な損失をもたらす、中間体多硫化物イオンが形成されること、[JP2015506539.pdf] また、製造面においても硫酸ナトリウムを炭素によって硫化リチウムに還元するには、高温の加熱工程が必要なこと、[JP7082405B.pdf] 守護地頭という重要な政策を確立しました。[info2.txt]

###
Question: '{q}'?

Sources:
{retrieved}

Answer:
"""

    def __init__(self, search_client: SearchClient, openai_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.openai_deployment = openai_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field

    def run(self, q: str, overrides: dict) -> any:
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        if overrides.get("semantic_ranker"):
            r = self.search_client.search(q, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language="ja-jp", 
                                          query_speller="none", 
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None)
        else:
            r = self.search_client.search(q, filter=filter, top=top)
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        prompt = (overrides.get("prompt_template") or self.template).format(q=q, retrieved=content)
        completion = openai.Completion.create(
            engine=self.openai_deployment, 
            prompt=prompt, 
            temperature=overrides.get("temperature") or 0.3, 
            max_tokens=1024, 
            n=1, 
            stop=["\n"])

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
