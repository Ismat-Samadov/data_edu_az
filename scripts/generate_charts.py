#!/usr/bin/env python3
"""
Data.edu.az Certificate Analytics
Business Insights Chart Generator

Generates business-focused visualizations for executive decision-making.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np
from pathlib import Path
import re

# Set professional style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11

# Create charts directory
Path("charts").mkdir(exist_ok=True)

# Load data
print("Loading certificate data...")
df = pd.read_csv('data/certificates.csv')

# Parse dates (Azerbaijani month names)
month_map = {
    'Yanvar': '01', 'Fevral': '02', 'Mart': '03', 'Aprel': '04',
    'May': '05', 'İyun': '06', 'İyul': '07', 'Avqust': '08',
    'Sentyabr': '09', 'Oktyabr': '10', 'Noyabr': '11', 'Dekabr': '12'
}

def parse_date(date_str):
    """Parse Azerbaijani date format"""
    if pd.isna(date_str):
        return None
    try:
        for az_month, num_month in month_map.items():
            if az_month in date_str:
                date_str = date_str.replace(az_month, num_month)
                break
        parts = date_str.split()
        if len(parts) == 3:
            day, month, year = parts
            return pd.to_datetime(f"{year}-{month}-{day.zfill(2)}", errors='coerce')
    except:
        pass
    return None

df['Completion_Date_Parsed'] = df['Completion Date'].apply(parse_date)
df['Year'] = df['Completion_Date_Parsed'].dt.year

# Fix data quality issue: Certificate 2023273 has wrong year (2013 should be 2023)
# Certificate ID pattern indicates 2023, not 2013
df.loc[(df['Certificate ID'] == 2023273) & (df['Year'] == 2013), 'Year'] = 2023
df.loc[(df['Certificate ID'] == 2023273) & (df['Year'] == 2023), 'Completion_Date_Parsed'] = pd.to_datetime('2023-10-18')

df['Month'] = df['Completion_Date_Parsed'].dt.month
df['Quarter'] = df['Completion_Date_Parsed'].dt.quarter
df['Year_Month'] = df['Completion_Date_Parsed'].dt.to_period('M')

print(f"Analyzing {len(df)} certificates from {df['Year'].min():.0f} to {df['Year'].max():.0f}")

# ============================================================================
# CHART 1: Course Portfolio Performance
# ============================================================================
print("Generating Chart 1: Course Portfolio Performance...")

plt.figure(figsize=(14, 8))
course_counts = df['Course Name'].value_counts().head(10)
colors = sns.color_palette("viridis", len(course_counts))

bars = plt.barh(range(len(course_counts)), course_counts.values, color=colors)
plt.yticks(range(len(course_counts)), course_counts.index)
plt.xlabel('Total Completions', fontsize=12, fontweight='bold')
plt.title('Top 10 Courses by Enrollment Volume', fontsize=16, fontweight='bold', pad=20)
plt.gca().invert_yaxis()

# Add value labels
for i, (bar, value) in enumerate(zip(bars, course_counts.values)):
    plt.text(value + 5, i, f'{value:,}', va='center', fontweight='bold')

plt.tight_layout()
plt.savefig('charts/01_course_portfolio_performance.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 2: Annual Growth Trajectory
# ============================================================================
print("Generating Chart 2: Annual Growth Trajectory...")

plt.figure(figsize=(14, 8))
yearly_completions = df.groupby('Year').size().sort_index()

bars = plt.bar(yearly_completions.index, yearly_completions.values,
               color=sns.color_palette("coolwarm", len(yearly_completions)),
               edgecolor='black', linewidth=1.5)

plt.xlabel('Year', fontsize=12, fontweight='bold')
plt.ylabel('Certificate Completions', fontsize=12, fontweight='bold')
plt.title('Annual Certificate Completion Trend', fontsize=16, fontweight='bold', pad=20)

# Add value labels and growth indicators
for i, (bar, year, value) in enumerate(zip(bars, yearly_completions.index, yearly_completions.values)):
    plt.text(year, value + 5, f'{value:,}', ha='center', fontweight='bold', fontsize=11)
    if i > 0:
        prev_value = yearly_completions.values[i-1]
        growth = ((value - prev_value) / prev_value * 100)
        color = 'green' if growth > 0 else 'red'
        plt.text(year, value/2, f'{growth:+.0f}%', ha='center',
                color=color, fontweight='bold', fontsize=10)

plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('charts/02_annual_growth_trajectory.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 3: Seasonal Enrollment Patterns
# ============================================================================
print("Generating Chart 3: Seasonal Enrollment Patterns...")

plt.figure(figsize=(14, 8))
monthly_data = df.groupby(['Year', 'Month']).size().reset_index(name='Count')
pivot_data = monthly_data.pivot(index='Month', columns='Year', values='Count').fillna(0)

month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

x = np.arange(12)
width = 0.15
years = sorted(pivot_data.columns)

for i, year in enumerate(years[-5:]):  # Last 5 years
    values = [pivot_data.loc[m, year] if m in pivot_data.index else 0 for m in range(1, 13)]
    plt.bar(x + i*width, values, width, label=int(year))

plt.xlabel('Month', fontsize=12, fontweight='bold')
plt.ylabel('Completions', fontsize=12, fontweight='bold')
plt.title('Monthly Enrollment Patterns by Year', fontsize=16, fontweight='bold', pad=20)
plt.xticks(x + width*2, month_names)
plt.legend(title='Year', loc='upper left')
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('charts/03_seasonal_enrollment_patterns.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 4: Market Segment Analysis (Course Categories)
# ============================================================================
print("Generating Chart 4: Market Segment Analysis...")

# Categorize courses
def categorize_course(course_name):
    if pd.isna(course_name):
        return 'Other'
    course_lower = course_name.lower()
    if 'excel' in course_lower:
        return 'Spreadsheet Analytics'
    elif 'python' in course_lower or 'r' in course_lower:
        return 'Data Science & Programming'
    elif 'sql' in course_lower or 'database' in course_lower or 'pl/sql' in course_lower:
        return 'Database Management'
    elif 'power bi' in course_lower or 'tableau' in course_lower:
        return 'Business Intelligence'
    elif 'hr' in course_lower or 'analytics' in course_lower:
        return 'Business Analytics'
    else:
        return 'Other'

df['Category'] = df['Course Name'].apply(categorize_course)

plt.figure(figsize=(14, 8))
category_counts = df['Category'].value_counts()
colors = sns.color_palette("Set2", len(category_counts))

bars = plt.barh(range(len(category_counts)), category_counts.values, color=colors)
plt.yticks(range(len(category_counts)), category_counts.index)
plt.xlabel('Total Enrollments', fontsize=12, fontweight='bold')
plt.title('Market Segment Distribution', fontsize=16, fontweight='bold', pad=20)
plt.gca().invert_yaxis()

for i, (bar, value) in enumerate(zip(bars, category_counts.values)):
    percentage = (value / len(df) * 100)
    plt.text(value + 10, i, f'{value:,} ({percentage:.1f}%)',
            va='center', fontweight='bold')

plt.tight_layout()
plt.savefig('charts/04_market_segment_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 5: Quarterly Performance Trends
# ============================================================================
print("Generating Chart 5: Quarterly Performance...")

plt.figure(figsize=(14, 8))
df['Year_Quarter'] = df['Year'].astype(str) + '-Q' + df['Quarter'].astype(str)
quarterly_data = df.groupby('Year_Quarter').size().sort_index()

# Only show recent quarters for clarity
recent_quarters = quarterly_data.tail(16)

plt.plot(range(len(recent_quarters)), recent_quarters.values,
         marker='o', linewidth=3, markersize=10, color='#2E86AB')
plt.fill_between(range(len(recent_quarters)), recent_quarters.values,
                 alpha=0.3, color='#2E86AB')

plt.xticks(range(len(recent_quarters)), recent_quarters.index, rotation=45, ha='right')
plt.xlabel('Quarter', fontsize=12, fontweight='bold')
plt.ylabel('Completions', fontsize=12, fontweight='bold')
plt.title('Quarterly Completion Trends (Last 4 Years)', fontsize=16, fontweight='bold', pad=20)

# Add value labels
for i, value in enumerate(recent_quarters.values):
    plt.text(i, value + 5, f'{value:,}', ha='center', fontsize=9, fontweight='bold')

plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('charts/05_quarterly_performance_trends.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 6: Top Courses Year-over-Year Growth
# ============================================================================
print("Generating Chart 6: Course Growth Analysis...")

top_courses = df['Course Name'].value_counts().head(5).index
course_yearly = df[df['Course Name'].isin(top_courses)].groupby(['Year', 'Course Name']).size().unstack(fill_value=0)

plt.figure(figsize=(14, 8))
course_yearly_recent = course_yearly.iloc[-5:]  # Last 5 years

ax = course_yearly_recent.plot(kind='bar', width=0.8)
plt.xlabel('Year', fontsize=12, fontweight='bold')
plt.ylabel('Completions', fontsize=12, fontweight='bold')
plt.title('Top 5 Courses: Year-over-Year Performance', fontsize=16, fontweight='bold', pad=20)
plt.legend(title='Course', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=0)
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('charts/06_top_courses_yoy_growth.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 7: Student Retention Analysis (Repeat Learners)
# ============================================================================
print("Generating Chart 7: Student Engagement Analysis...")

student_course_counts = df.groupby('Student Name').size().value_counts().sort_index()

plt.figure(figsize=(14, 8))
bars = plt.bar(student_course_counts.index, student_course_counts.values,
               color='#A23B72', edgecolor='black', linewidth=1.5)

plt.xlabel('Number of Courses Completed', fontsize=12, fontweight='bold')
plt.ylabel('Number of Students', fontsize=12, fontweight='bold')
plt.title('Student Engagement Level Distribution', fontsize=16, fontweight='bold', pad=20)

# Add labels
for bar, value in zip(bars, student_course_counts.values):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 5,
            f'{int(value):,}', ha='center', fontweight='bold')

# Calculate metrics
total_students = df['Student Name'].nunique()
repeat_students = df[df.duplicated(subset=['Student Name'], keep=False)]['Student Name'].nunique()
retention_rate = (repeat_students / total_students) * 100

plt.text(0.98, 0.97, f'Retention Rate: {retention_rate:.1f}%\nTotal Students: {total_students:,}',
         transform=plt.gca().transAxes, ha='right', va='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
         fontsize=11, fontweight='bold')

plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('charts/07_student_engagement_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 8: Course Completion Heatmap
# ============================================================================
print("Generating Chart 8: Completion Timing Heatmap...")

heatmap_data = df.groupby(['Month', 'Year']).size().unstack(fill_value=0)

plt.figure(figsize=(14, 10))
sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='YlOrRd',
            cbar_kws={'label': 'Completions'}, linewidths=0.5)

plt.xlabel('Year', fontsize=12, fontweight='bold')
plt.ylabel('Month', fontsize=12, fontweight='bold')
plt.title('Completion Volume Heatmap (Month vs Year)', fontsize=16, fontweight='bold', pad=20)
plt.yticks(np.arange(12) + 0.5, month_names, rotation=0)
plt.tight_layout()
plt.savefig('charts/08_completion_timing_heatmap.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 9: Portfolio Concentration Risk
# ============================================================================
print("Generating Chart 9: Portfolio Concentration Analysis...")

plt.figure(figsize=(14, 8))
course_percentages = (df['Course Name'].value_counts() / len(df) * 100).head(10)

bars = plt.barh(range(len(course_percentages)), course_percentages.values,
               color=sns.color_palette("rocket_r", len(course_percentages)))
plt.yticks(range(len(course_percentages)), course_percentages.index)
plt.xlabel('Market Share (%)', fontsize=12, fontweight='bold')
plt.title('Course Portfolio Concentration (Top 10)', fontsize=16, fontweight='bold', pad=20)
plt.gca().invert_yaxis()

# Add reference line for 10%
plt.axvline(x=10, color='red', linestyle='--', linewidth=2, alpha=0.7, label='10% Threshold')

for i, (bar, value) in enumerate(zip(bars, course_percentages.values)):
    plt.text(value + 0.3, i, f'{value:.1f}%', va='center', fontweight='bold')

plt.legend()
plt.tight_layout()
plt.savefig('charts/09_portfolio_concentration_risk.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# CHART 10: Growth Momentum Indicator
# ============================================================================
print("Generating Chart 10: Growth Momentum...")

# Calculate rolling 12-month completions
df_sorted = df.sort_values('Completion_Date_Parsed').copy()
df_sorted = df_sorted[df_sorted['Completion_Date_Parsed'].notna()]
df_sorted.set_index('Completion_Date_Parsed', inplace=True)

# Create a dummy column to count
df_sorted['count'] = 1
df_sorted['Rolling_12M'] = df_sorted['count'].rolling('365D', min_periods=1).sum()
df_sorted.reset_index(inplace=True)

# Sample by month for clarity
sampled = df_sorted.groupby(df_sorted['Completion_Date_Parsed'].dt.to_period('M')).last()

plt.figure(figsize=(14, 8))
plt.plot(range(len(sampled)), sampled['Rolling_12M'].values,
        linewidth=3, color='#06A77D', marker='o', markersize=6)
plt.fill_between(range(len(sampled)), sampled['Rolling_12M'].values,
                alpha=0.3, color='#06A77D')

plt.xlabel('Time Period', fontsize=12, fontweight='bold')
plt.ylabel('12-Month Rolling Completions', fontsize=12, fontweight='bold')
plt.title('Growth Momentum: 12-Month Rolling Average', fontsize=16, fontweight='bold', pad=20)

# Show recent period labels
step = max(1, len(sampled) // 15)
plt.xticks(range(0, len(sampled), step),
          [str(p) for p in sampled.index[::step]], rotation=45, ha='right')

plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('charts/10_growth_momentum_indicator.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# Generate Summary Statistics
# ============================================================================
print("\nGenerating summary statistics...")

summary_stats = {
    'total_certificates': len(df),
    'total_students': df['Student Name'].nunique(),
    'total_courses': df['Course Name'].nunique(),
    'years_operating': int(df['Year'].max() - df['Year'].min() + 1),
    'avg_annual_completions': len(df) / (df['Year'].max() - df['Year'].min() + 1),
    'top_course': df['Course Name'].value_counts().index[0],
    'top_course_count': df['Course Name'].value_counts().values[0],
    'retention_rate': (repeat_students / total_students) * 100,
    'peak_year': int(df['Year'].value_counts().index[0]),
    'peak_year_count': int(df['Year'].value_counts().values[0]),
    'yoy_growth_2024_2025': ((df[df['Year'] == 2025].shape[0] - df[df['Year'] == 2024].shape[0]) /
                              df[df['Year'] == 2024].shape[0] * 100) if 2025 in df['Year'].values and 2024 in df['Year'].values else 0,
}

# Save statistics
with open('charts/summary_statistics.txt', 'w') as f:
    f.write("DATA.EDU.AZ CERTIFICATE ANALYTICS SUMMARY\n")
    f.write("=" * 50 + "\n\n")
    for key, value in summary_stats.items():
        if isinstance(value, float):
            f.write(f"{key}: {value:.1f}\n")
        else:
            f.write(f"{key}: {value}\n")

print("\n" + "="*70)
print("✅ ALL CHARTS GENERATED SUCCESSFULLY")
print("="*70)
print(f"Total Charts Created: 10")
print(f"Output Directory: charts/")
print(f"Summary Statistics: charts/summary_statistics.txt")
print("="*70)
