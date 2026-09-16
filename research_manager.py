import asyncio
from agents import Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from email_agent import email_agent
from utils import pre_filter_and_deduplicate, is_simple_query, save_report

class ResearchManager:

    async def run(self, query: str):
        """ Run the deep research process with Intent Routing & Data Pre-Filtering """
        trace_id = gen_trace_id()
        
        with trace("Research trace", trace_id=trace_id):
            yield f"Starting research. Trace: https://openai.com{trace_id}"
            print(f"Starting research. Trace: https://openai.com{trace_id}")
            
            # --- OPTIMIZATION: INTENTION ROUTING ---
            if is_simple_query(query):
                yield "Simple query detected. Bypassing Search and Planner tracks via Intention Routing..."
                print("Simple query detected. Bypassing Search and Planner tracks via Intention Routing...")
                
                # Pass an explicit systemic system-prompt instruction modifier to the writer
                instruction_modifier = (
                    "\nNOTE: You are in DIRECT KNOWLEDGE MODE. The search index was bypassed for efficiency. "
                    "Please answer this straightforward query comprehensively using your own pre-trained internal knowledge base in a single page summary."
                )
                
                report = await self.write_report(query + instruction_modifier, ["Direct LLM routing active."])
                saved_path = save_report(query, report.markdown_report, trace_id)
                yield f"Report saved to {saved_path}", str(saved_path)

                yield "Report written, sending email..."
                await self.send_email(report)
                yield "Email sent, research complete"
                yield report.markdown_report, str(saved_path)
                return  # Terminate early to bypass complex loops

            # --- STANDARD TRACK (COMPLEX RESEARCH) ---
            search_plan = await self.plan_searches(query)
            yield f"Searches planned, starting {len(search_plan.searches)} searches..."     
            
            # Perform original web fetching tasks
            raw_search_results = await self.perform_searches(search_plan)
            
            # --- OPTIMIZATIONS: DEDUPLICATION & PRE-FILTERING ---
            yield "Filtering content, deduplicating search clusters..."
            optimized_search_results = pre_filter_and_deduplicate(raw_search_results)
            
            yield "Searches optimized and summarized, writing report..."
            report = await self.write_report(query, optimized_search_results)
            saved_path = save_report(query, report.markdown_report, trace_id)
            yield f"Report saved to {saved_path}", str(saved_path)

            yield "Report written, sending email..."
            await self.send_email(report)
            yield "Email sent, research complete"
            yield report.markdown_report, str(saved_path)

    async def plan_searches(self, query: str) -> WebSearchPlan:
        """ Plan the searches to perform for the query """
        result = await Runner.run(planner_agent, f"Query: {query}")
        return result.final_output

    async def perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        """ Perform the searches to perform for the query """
        tasks = [self.search(item) for item in search_plan.searches]
        return await asyncio.gather(*tasks)

    async def search(self, item: WebSearchItem) -> str | None:
        """ Perform a search for the query """
        input_message = f"Search term: {item.query}\nReason for searching: {item.reason}"
        result = await Runner.run(search_agent, input_message)
        return result.final_output

    async def write_report(self, query: str, search_results: list[str]) -> ReportData:
        """ Write the report for the query """
        input_message = f"Original query: {query}\nSummarized search results: {search_results}"
        result = await Runner.run(writer_agent, input_message)
        return result.final_output
    
    async def send_email(self, report: ReportData) -> None:
        await Runner.run(email_agent, report.markdown_report)
