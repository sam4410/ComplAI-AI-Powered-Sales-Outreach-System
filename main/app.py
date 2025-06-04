import streamlit as st
import os
from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from typing import Dict
import sendgrid
from sendgrid.helpers.mail import Mail
import asyncio
import time

# Load environment variables
load_dotenv(override=True)

# Set page config
st.set_page_config(
    page_title="ComplAI Sales Outreach",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for elegant design
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .agent-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .process-step {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
    }
    
    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'email_sent' not in st.session_state:
    st.session_state.email_sent = False
if 'result' not in st.session_state:
    st.session_state.result = None

# Header
st.markdown("""
<div class="main-header">
    <h1>📧 ComplAI Sales Outreach System</h1>
    <p>AI-Powered Cold Email Generation & Automation</p>
</div>
""", unsafe_allow_html=True)

# Sidebar with system information
with st.sidebar:
    st.header("🤖 System Overview")
    
    st.markdown("""
    ### Purpose
    ComplAI's automated sales outreach system generates and sends personalized cold emails to potential customers for our SOC 2 compliance SaaS platform.
    """)
    
    st.markdown("""
    ### Process Flow
    1. **Message Input** - Specify target recipient
    2. **Multi-Agent Generation** - 3 specialized agents create different email styles
    3. **Selection & Optimization** - Sales manager picks the best version
    4. **Email Processing** - Subject generation & HTML formatting
    5. **Automated Delivery** - Send via SendGrid
    """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 📊 Agent Profiles
    """)

# Agent descriptions in expandable sections
col1, col2 = st.columns(2)

with col1:
    with st.expander("👔 Professional Sales Agent"):
        st.markdown("""
        **Style**: Professional & Serious
        - Formal tone and structure
        - Emphasis on credibility
        - Direct value proposition
        - Corporate-friendly language
        """)
    
    with st.expander("🎭 Engaging Sales Agent"):
        st.markdown("""
        **Style**: Witty & Engaging
        - Humorous approach
        - Conversational tone
        - Creative hooks
        - High response likelihood
        """)

with col2:
    with st.expander("⚡ Busy Sales Agent"):
        st.markdown("""
        **Style**: Concise & Direct
        - Brief and to-the-point
        - Time-conscious messaging
        - Quick value delivery
        - Efficient communication
        """)
    
    with st.expander("📝 Support Agents"):
        st.markdown("""
        **Subject Writer**: Crafts compelling subject lines
        **HTML Converter**: Creates professional email layouts
        **Email Manager**: Orchestrates the sending process
        """)

# Main content area
st.markdown("## 📨 Generate Sales Email")

# Input section
with st.container():
    st.markdown("### Target Recipient Information")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        recipient_message = st.text_area(
            "Describe your target recipient:",
            placeholder="e.g., Send a cold sales email addressed to Dear CEO from Alice, a fintech startup founder who needs SOC 2 compliance for their growing company",
            help="Provide details about who you're targeting - their role, company, industry, or specific needs",
            height=100
        )
    
    with col2:
        st.markdown("### Email Configuration")
        
        # Check if SendGrid is configured
        sendgrid_configured = bool(os.environ.get("SENDGRID_API_KEY"))
        
        if sendgrid_configured:
            st.success("✅ SendGrid Configured")
        else:
            st.error("❌ SendGrid Not Configured")
            st.caption("Please set SENDGRID_API_KEY environment variable")
        
        generate_button = st.button(
            "🚀 Generate & Send Email", 
            type="primary",
            disabled=not recipient_message.strip() or not sendgrid_configured,
            use_container_width=True
        )

# Define all the agents and tools (same as original code)
@st.cache_resource
def initialize_agents():
    # Sales agent instructions
    instructions1 = """
    You are a sales agent working for ComplAI, a company that provides a SaaS tool for ensuring SOC 2 compliance
    and preparing for SOC 2 audits, powered by AI.
    You write professional, serious cold emails to potential customers.
    """
    
    instructions2 = """
    You are humorous, engaging sales agent working for ComplAI, a company that provides a SaaS tool for ensuring SOC 2 compliance
    and preparing for SOC 2 audits, powered by AI.
    You write witty, engaging cold email that are likely to get responses.
    """
    
    instructions3 = """
    You are a busy sales agent working for ComplAI, a company that provides a SaaS tool for ensuring SOC 2 compliance
    and preparing for SOC 2 audits, powered by AI.
    You write concise, to the point cold emails.
    """
    
    # Build agents
    sales_agent1 = Agent(name="Professional Sales Agent", instructions=instructions1, model="gpt-4o-mini")
    sales_agent2 = Agent(name="Engaging Sales Agent", instructions=instructions2, model="gpt-4o-mini")
    sales_agent3 = Agent(name="Busy Sales Agent", instructions=instructions3, model="gpt-4o-mini")
    
    # Create tools
    tool1 = sales_agent1.as_tool(tool_name="sales_agent1", tool_description="A sales agent that writes professional, serious cold emails")
    tool2 = sales_agent2.as_tool(tool_name="sales_agent2", tool_description="A sales agent that writes witty, engaging cold emails")
    tool3 = sales_agent3.as_tool(tool_name="sales_agent3", tool_description="A sales agent that writes concise, to the point cold emails")
    
    # Subject and HTML agents
    subject_writer = Agent(
        name="Subject Writer",
        instructions="You can write a subject for a cold sales email. You are given a message and you need to write a subject for and email that is highly likely to get a response.",
        model="gpt-4o-mini"
    )
    
    html_converter = Agent(
        name="HTML Converter", 
        instructions="You can convert a text email body into an html email body. You are given a text email body which might have some markdown and you need to convert it into an html email body with simple, clear, compelling layout and design.",
        model="gpt-4o-mini"
    )
    
    subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="A tool that writes a subject for a cold sales email")
    html_tool = html_converter.as_tool(tool_name="html_converter", tool_description="A tool that converts a text email body into an html email body")
    
    return tool1, tool2, tool3, subject_tool, html_tool

@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """send out an html email with the given subject and body to all sales prospects"""
    try:
        sg = sendgrid.SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY"))
        
        mail = Mail(
            from_email="deepikamanojsharma84@gmail.com",
            to_emails="sharma.manoj84@yahoo.co.in",
            subject=subject,
            html_content=html_body
        )
        
        response = sg.send(mail)
        
        return {
            "status": "success", 
            "message": f"Email sent successfully. Status code: {response.status_code}"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}

# Email generation process
if generate_button and recipient_message.strip():
    with st.spinner("🤖 Initializing AI agents..."):
        tool1, tool2, tool3, subject_tool, html_tool = initialize_agents()
        
        # Create emailer agent
        emailer_agent = Agent(
            name="Email Manager",
            instructions="""
            You are an email manager working for ComplAI. You are responsible for formatting and sending out emails.
            You take the email content provided to you and:
            1. Generate an appropriate subject line using the subject_writer tool
            2. Convert the email body to HTML format using the html_converter tool
            3. Send the email using the send_html_email tool
            You always complete all three steps in order.
            """,
            tools=[subject_tool, html_tool, send_html_email],
            model="gpt-4o-mini"
        )
        
        # Create sales manager
        sales_manager = Agent(
            name="Sales Manager",
            instructions="""
            You are a sales manager working for ComplAI. You use the tools given to you to generate cold sales emails.
            You never generate sales emails yourself; you only use the tools to generate them.
            Your process:
            1. Use all 3 sales_agent tools (sales_agent1, sales_agent2, sales_agent3) to generate different email versions
            2. Compare the results and pick the single best email using your judgment
            3. Once you have selected the best email, hand it off to the Email Manager exactly once
            Important: You should only request handoff to Email Manager once you have the final email content ready.
            Do not request multiple handoffs - only one handoff after you've completed your evaluation.
            """,
            tools=[tool1, tool2, tool3],
            handoffs=[emailer_agent],
            model="gpt-4o-mini"
        )
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    async def run_email_generation():
        try:
            status_text.text("🎯 Analyzing target recipient...")
            progress_bar.progress(20)
            
            status_text.text("✍️ Generating email variations...")
            progress_bar.progress(40)
            
            status_text.text("🧠 Selecting best version...")
            progress_bar.progress(60)
            
            status_text.text("📝 Creating subject line and HTML...")
            progress_bar.progress(80)
            
            status_text.text("📧 Sending email...")
            progress_bar.progress(90)
            
            with trace("Automated Sales Outreach"):
                result = await Runner.run(sales_manager, recipient_message)
            
            progress_bar.progress(100)
            status_text.text("✅ Email sent successfully!")
            
            return result
            
        except Exception as e:
            st.error(f"❌ Error during email generation: {str(e)}")
            return None
    
    # Run the async function
    try:
        result = asyncio.run(run_email_generation())
        st.session_state.result = result
        st.session_state.email_sent = True
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        st.error(f"❌ Failed to process request: {str(e)}")

# Display results
if st.session_state.email_sent and st.session_state.result:
    st.markdown("---")
    st.markdown("## 📊 Campaign Results")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="success-message">
            <h4>✅ Email Campaign Completed Successfully!</h4>
            <p>Your AI-generated sales email has been processed and sent to the target recipient.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 View Campaign Details"):
            st.json(st.session_state.result)
    
    with col2:
        st.markdown("### 📈 Next Steps")
        st.markdown("""
        - Monitor email engagement
        - Track response rates
        - Follow up if needed
        - Analyze performance metrics
        """)
        
        if st.button("🔄 Send Another Email", use_container_width=True):
            st.session_state.email_sent = False
            st.session_state.result = None
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🚀 Powered by ComplAI | AI-Driven Sales Automation</p>
    <p><small>Streamlining SOC 2 compliance for modern businesses</small></p>
</div>
""", unsafe_allow_html=True)
